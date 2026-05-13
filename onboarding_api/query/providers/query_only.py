"""
query/providers/query_only.py

Strategy: ``query_only``

Direct LLM query — no vector retrieval.  Useful when:
  - The question is general knowledge (no document lookup needed).
  - The QueryPlanner determined retrieval is unnecessary.
  - You want to measure LLM-only vs RAG quality.

The QueryPlanner still runs to decide output format (table|chart|form|text),
and the QueryExecutor still renders the result.
"""

from typing import Any, Optional

from query.base import (
    BaseQueryStrategy,
    ExecutionConfig,
    QueryDbConfig,
    QueryModeConfig,
    QueryPlannerConfig,
    QueryResult,
)
from query.executor import QueryExecutor
from query.planner import QueryPlanner


class QueryOnlyQuery(BaseQueryStrategy):
    """
    Direct LLM query with no retrieval step.

    Config used
    -----------
        query_mode.strategy       : query_only
        query_planner.model       : LLM model for answer generation
        query_planner.rules_enabled: whether to use rule-based planner
        execution.*               : controls output rendering format
    """

    def __init__(
        self,
        mode_config: QueryModeConfig,
        planner_config: QueryPlannerConfig,
        execution_config: ExecutionConfig,
        db_config: Optional[QueryDbConfig] = None,
    ):
        super().__init__(mode_config, planner_config, execution_config, db_config)
        self._planner = QueryPlanner(planner_config, execution_config)
        self._executor = QueryExecutor(execution_config)

    # ------------------------------------------------------------------
    # BaseQueryStrategy interface
    # ------------------------------------------------------------------

    def execute(self, query_text: str, index: Any = None, **kwargs) -> QueryResult:
        """
        Send the query directly to the LLM without retrieval.

        Args:
            query_text: Natural language query.
            index:      Ignored in this strategy (accepted for API consistency).
            **kwargs:   Optional LLM overrides (e.g. temperature, max_tokens).

        Returns:
            QueryResult with answer and rendered output (no source_nodes).
        """
        print(f"[QueryOnlyQuery] Direct LLM query: {query_text[:80]!r}...")

        # Step 1 — Query planning (for output format)
        decision = self._planner.plan(query_text)
        print(f"[QueryOnlyQuery] Planner decision: {decision}")

        effective_query = decision.rewritten_query or query_text

        # Step 2 — Generate answer (no retrieval)
        answer = self._generate_answer(
            query=effective_query,
            model=self.planner_config.model,
            **kwargs,
        )

        # Step 3 — Render
        result = QueryResult(
            answer=answer,
            strategy="query_only",
            source_nodes=[],
            output_format=decision.output_format,
            metadata={
                "query": query_text,
                "rewritten_query": decision.rewritten_query,
                "planner_reasoning": decision.reasoning,
            },
        )
        return self._executor.render(result)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _generate_answer(query: str, model: str, **kwargs) -> str:
        """
        Call the configured LLM directly.

        Scaffold: replace with your LLM client call.

        Example (OpenAI)::

            from openai import OpenAI
            client = OpenAI()
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": query}],
                temperature=kwargs.get("temperature", 0.2),
                max_tokens=kwargs.get("max_tokens", 1024),
            )
            return resp.choices[0].message.content
        """
        print(
            f"[QueryOnlyQuery] LLM call scaffold (model={model!r}). "
            f"Query length: {len(query)} chars."
        )
        return (
            f"[LLM:{model}] Direct answer to: {query!r}\n"
            f"(Replace this scaffold with a real LLM client call.)"
        )
