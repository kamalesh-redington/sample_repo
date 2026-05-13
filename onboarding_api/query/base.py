"""
query/base.py — Abstract base classes and config dataclasses for the query module.

Every concrete query strategy in ``query/providers/`` MUST inherit from
``BaseQueryStrategy`` and implement ``execute()``.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


# ── Config dataclasses ─────────────────────────────────────────────────────────

@dataclass
class QueryModeConfig:
    """
    Maps to config.yaml → query_mode section.

        query_mode:
          enabled: true
          strategy: hybrid        # rag | query_only | hybrid
    """
    enabled: bool = True
    strategy: str = "hybrid"     # rag | query_only | hybrid

    @classmethod
    def from_config(cls, config: dict) -> "QueryModeConfig":
        qm = config.get("query_mode", {})
        return cls(
            enabled=qm.get("enabled", True),
            strategy=qm.get("strategy", "hybrid"),
        )


@dataclass
class QueryPlannerConfig:
    """
    Maps to config.yaml → query_planner section.

        query_planner:
          model: qwen-mini
          rules_enabled: true
    """
    model: str = "qwen-mini"
    rules_enabled: bool = True
    extra: dict = field(default_factory=dict)

    @classmethod
    def from_config(cls, config: dict) -> "QueryPlannerConfig":
        qp = config.get("query_planner", {})
        known = {"model", "rules_enabled"}
        return cls(
            model=qp.get("model", "qwen-mini"),
            rules_enabled=qp.get("rules_enabled", True),
            extra={k: v for k, v in qp.items() if k not in known},
        )


@dataclass
class ExecutionConfig:
    """
    Maps to config.yaml → execution section.

        execution:
          enable_table: true
          enable_chart: true
          enable_form: true
          enable_text: true
    """
    enable_table: bool = True
    enable_chart: bool = True
    enable_form: bool = True
    enable_text: bool = True

    @classmethod
    def from_config(cls, config: dict) -> "ExecutionConfig":
        ex = config.get("execution", {})
        return cls(
            enable_table=ex.get("enable_table", True),
            enable_chart=ex.get("enable_chart", True),
            enable_form=ex.get("enable_form", True),
            enable_text=ex.get("enable_text", True),
        )

    def enabled_formats(self) -> List[str]:
        """Return list of enabled output format names."""
        formats = []
        if self.enable_table: formats.append("table")
        if self.enable_chart: formats.append("chart")
        if self.enable_form:  formats.append("form")
        if self.enable_text:  formats.append("text")
        return formats


@dataclass
class QueryDbConfig:
    """
    Parsed representation of query/db_config.yaml.

    Use ``QueryDbConfig.from_yaml()`` to load from disk.
    """
    vector_db: dict = field(default_factory=dict)
    relational_db: dict = field(default_factory=dict)
    cache: dict = field(default_factory=dict)
    audit: dict = field(default_factory=dict)

    @classmethod
    def from_yaml(cls, path: Optional[str] = None) -> "QueryDbConfig":
        """Load query/db_config.yaml from disk."""
        if path is None:
            path = str(Path(__file__).resolve().parent / "db_config.yaml")
        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        raw = raw or {}
        return cls(
            vector_db=raw.get("vector_db", {}),
            relational_db=raw.get("relational_db", {}),
            cache=raw.get("cache", {}),
            audit=raw.get("audit", {}),
        )

    @classmethod
    def from_config(cls, config: dict) -> "QueryDbConfig":
        """
        Build QueryDbConfig from the inline ``query_db`` section of config.yaml.

        Falls back to loading ``query/db_config.yaml`` from disk only if
        ``query_db`` is absent from the config dict.
        """
        if "query_db" in config:
            raw = config["query_db"] or {}
            return cls(
                vector_db=raw.get("vector_db", {}),
                relational_db=raw.get("relational_db", {}),
                cache=raw.get("cache", {}),
                audit=raw.get("audit", {}),
            )
        # Legacy fallback: load from separate file
        db_path = config.get("query", {}).get("db_config_path")
        return cls.from_yaml(db_path)


# ── Query result ───────────────────────────────────────────────────────────────

@dataclass
class QueryResult:
    """
    Unified result returned by every BaseQueryStrategy.execute() call.
    """
    answer: str                               # LLM-generated answer text
    strategy: str                             # which strategy produced this
    source_nodes: List[Any] = field(default_factory=list)  # retrieved chunks
    metadata: Dict[str, Any] = field(default_factory=dict)
    output_format: str = "text"               # table | chart | form | text
    rendered: Optional[Any] = None            # rendered output (DataFrame, dict, etc.)

    def __repr__(self) -> str:
        return (
            f"QueryResult(strategy={self.strategy!r}, "
            f"format={self.output_format!r}, "
            f"answer_len={len(self.answer)})"
        )


# ── Abstract base ──────────────────────────────────────────────────────────────

class BaseQueryStrategy(ABC):
    """
    Abstract base for every query strategy.

    All concrete strategies MUST implement:
        execute(query_text, index, **kwargs) → QueryResult
    """

    def __init__(
        self,
        mode_config: QueryModeConfig,
        planner_config: QueryPlannerConfig,
        execution_config: ExecutionConfig,
        db_config: Optional[QueryDbConfig] = None,
    ):
        self.mode_config = mode_config
        self.planner_config = planner_config
        self.execution_config = execution_config
        self.db_config = db_config

    @abstractmethod
    def execute(self, query_text: str, index: Any, **kwargs) -> QueryResult:
        """
        Execute the query and return a QueryResult.

        Args:
            query_text: The natural language query string.
            index:      A VectorStoreIndex (or compatible object) for retrieval.
            **kwargs:   Strategy-specific overrides.

        Returns:
            A QueryResult instance.
        """

    def info(self) -> dict:
        """Return strategy metadata for logging."""
        return {
            "strategy": self.mode_config.strategy,
            "planner_model": self.planner_config.model,
            "rules_enabled": self.planner_config.rules_enabled,
            "output_formats": self.execution_config.enabled_formats(),
        }

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"strategy={self.mode_config.strategy!r}, "
            f"model={self.planner_config.model!r})"
        )
