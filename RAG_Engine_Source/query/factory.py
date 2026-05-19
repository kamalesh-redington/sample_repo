"""
QueryFactory — config-driven query strategy instantiation.

Usage
-----
    from query.factory import QueryFactory

    strategy = QueryFactory.create(config)
    result   = strategy.execute(query_text, index)

Supported strategies (config.query_mode.strategy)
-------------------------------------------------
    rag         → RAGQuery        vector retrieval → LLM answer
    query_only  → QueryOnlyQuery  direct LLM (no retrieval)
    hybrid      → HybridQuery     rag + query_only merged
"""

import importlib
from typing import Optional, Type

from query.base import (
    BaseQueryStrategy,
    ExecutionConfig,
    QueryDbConfig,
    QueryModeConfig,
    QueryPlannerConfig,
)


# ── Provider registry ──────────────────────────────────────────────────────────
# Lazy imports — SDKs are only pulled in when the strategy is actually used.

_REGISTRY: dict[str, str] = {
    "rag":        "query.providers.rag_query.RAGQuery",
    "query_only": "query.providers.query_only.QueryOnlyQuery",
    "hybrid":     "query.providers.hybrid_query.HybridQuery",
}


def _import_class(dotted_path: str) -> Type[BaseQueryStrategy]:
    """Lazily import a BaseQueryStrategy subclass from a dotted module path."""
    module_path, class_name = dotted_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


class QueryFactory:
    """
    Registry-based factory for query strategy instances.

    Reads ``config["query_mode"]["strategy"]`` and instantiates the
    appropriate ``BaseQueryStrategy`` subclass with all config sections.
    """

    @staticmethod
    def create(
        config: dict,
        db_config: Optional[QueryDbConfig] = None,
    ) -> BaseQueryStrategy:
        """
        Instantiate the appropriate query strategy from a config dict.

        Args:
            config:    Full application config dict (parsed config.yaml).
                       Reads: query_mode.strategy, query_planner.*, execution.*
            db_config: Optional pre-loaded QueryDbConfig.  If None, the factory
                       attempts to load ``query/db_config.yaml`` automatically.

        Returns:
            A concrete BaseQueryStrategy instance.

        Raises:
            ValueError:  query_mode.enabled is False or unknown strategy.
            ImportError: Required package not installed for that strategy.
        """
        mode_cfg = QueryModeConfig.from_config(config)

        if not mode_cfg.enabled:
            raise ValueError(
                "[QueryFactory] query_mode.enabled is false in config. "
                "Set it to true to use the query module."
            )

        strategy = mode_cfg.strategy.lower().strip()

        if strategy not in _REGISTRY:
            supported = ", ".join(sorted(_REGISTRY.keys()))
            raise ValueError(
                f"[QueryFactory] Unsupported query strategy: {strategy!r}.\n"
                f"Supported strategies: {supported}"
            )

        planner_cfg = QueryPlannerConfig.from_config(config)
        exec_cfg = ExecutionConfig.from_config(config)

        # Load db_config from query/db_config.yaml if not provided
        if db_config is None:
            try:
                db_config = QueryDbConfig.from_config(config)
            except FileNotFoundError:
                db_config = QueryDbConfig()   # empty defaults

        strategy_class = _import_class(_REGISTRY[strategy])

        print(
            f"[QueryFactory] Creating strategy: {strategy_class.__name__} "
            f"(strategy={strategy!r}, model={planner_cfg.model!r}, "
            f"formats={exec_cfg.enabled_formats()})"
        )

        return strategy_class(mode_cfg, planner_cfg, exec_cfg, db_config)

    @staticmethod
    def list_strategies() -> list[str]:
        """Return a sorted list of all registered strategy keys."""
        return sorted(_REGISTRY.keys())

    @staticmethod
    def register(strategy_key: str, dotted_class_path: str) -> None:
        """
        Register a custom query strategy at runtime.

        Args:
            strategy_key:       Key used in config.yaml (e.g. ``"agentic"``)
            dotted_class_path:  e.g. ``"myapp.query.agentic.AgenticQuery"``

        Example::

            QueryFactory.register(
                "agentic",
                "myapp.query.agentic_query.AgenticQuery"
            )
        """
        _REGISTRY[strategy_key.lower()] = dotted_class_path
        print(f"[QueryFactory] Registered custom strategy: {strategy_key!r}")
