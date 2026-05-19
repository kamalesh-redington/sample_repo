"""
query/providers/hybrid_query.py

Strategy: ``hybrid``

Runs BOTH the RAG strategy and the QueryOnly strategy in parallel, then
merges their answers using a configurable fusion approach.

Fusion modes (config.query_planner.extra.fusion_mode):
    weighted  — concatenate both answers with source labels (default)
    rag_first — prefer RAG answer, fall back to query_only if RAG has no nodes
    llm_merge — send both answers to the LLM to synthesise a final response

This is the default and recommended strategy as it gives the best coverage:
  - RAG handles document-grounded facts.
  - QueryOnly handles general knowledge and fills gaps.
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
from query.providers.rag_query import RAGQuery
from query.providers.query_only import QueryOnlyQuery


class HybridQuery(BaseQueryStrategy):
    """
    Hybrid query strategy combining RAG retrieval with direct LLM knowledge.

    Config used
    -----------
        query_mode.strategy               : hybrid
        query_planner.model               : LLM model
        query_planner.rules_enabled       : whether to use rule-based planner
        query_planner.extra.fusion_mode   : weighted | rag_first | llm_merge
        execution.*                       : output rendering flags
        query/db_config.yaml → vector_db  : retrieval settings
    """

    def __init__(
        self,
        mode_config: QueryModeConfig,
        planner_config: QueryPlannerConfig,
        execution_config: ExecutionConfig,
        db_config: Optional[QueryDbConfig] = None,
    ):
        super().__init__(mode_config, planner_config, execution_config, db_config)

        # Build sub-strategy instances (share same configs)
        self._rag = RAGQuery(mode_config, planner_config, execution_config, db_config)
        self._query_only = QueryOnlyQuery(mode_config, planner_config, execution_config, db_config)
        self._executor = QueryExecutor(execution_config)
        self._planner = QueryPlanner(planner_config, execution_config)

        self._fusion_mode: str = planner_config.extra.get("fusion_mode", "weighted")

    # ------------------------------------------------------------------
    # BaseQueryStrategy interface
    # ------------------------------------------------------------------

    def execute(self, query_text: str, index: Any, **kwargs) -> QueryResult:
        """
        Execute hybrid query: RAG + QueryOnly → fused answer.

        Args:
            query_text: Natural language query.
            index:      VectorStoreIndex for RAG retrieval.
            **kwargs:   Forwarded to both sub-strategies.

        Returns:
            A single fused QueryResult.
        """
        print(
            f"[HybridQuery] Executing hybrid query "
            f"(fusion_mode={self._fusion_mode!r}): {query_text[:80]!r}..."
        )

        # Step 1 — Planning (shared decision for output format)
        decision = self._planner.plan(query_text)
        print(f"[HybridQuery] Planner decision: {decision}")

        # Step 2 — Run both strategies
        rag_result = self._rag.execute(query_text, index, **kwargs)
        qo_result = self._query_only.execute(query_text, index=None, **kwargs)

        # Step 3 — Fuse
        fused_answer, fused_nodes = self._fuse(
            query_text, rag_result, qo_result, decision
        )

        # Step 4 — Render merged result
        result = QueryResult(
            answer=fused_answer,
            strategy="hybrid",
            source_nodes=fused_nodes,
            output_format=decision.output_format,
            metadata={
                "query": query_text,
                "fusion_mode": self._fusion_mode,
                "rag_nodes": len(rag_result.source_nodes),
                "planner_reasoning": decision.reasoning,
            },
        )
        return self._executor.render(result)

    # ------------------------------------------------------------------
    # Fusion helpers
    # ------------------------------------------------------------------

    def _fuse(
        self,
        query_text: str,
        rag_result: QueryResult,
        qo_result: QueryResult,
        decision,
    ):
        """Merge RAG and QueryOnly answers according to fusion_mode."""
        mode = self._fusion_mode

        if mode == "rag_first":
            return self._fuse_rag_first(rag_result, qo_result)

        if mode == "llm_merge":
            return self._fuse_llm_merge(query_text, rag_result, qo_result)

        # Default: weighted (concatenate both)
        return self._fuse_weighted(rag_result, qo_result)

    @staticmethod
    def _fuse_weighted(rag: QueryResult, qo: QueryResult):
        """Concatenate both answers with clear section labels."""
        answer = (
            "### 📄 From Documents (RAG)\n\n"
            f"{rag.answer}\n\n"
            "---\n\n"
            "### 🧠 From General Knowledge\n\n"
            f"{qo.answer}"
        )
        return answer, rag.source_nodes

    @staticmethod
    def _fuse_rag_first(rag: QueryResult, qo: QueryResult):
        """Use RAG answer if it has source nodes; otherwise fall back to QueryOnly."""
        if rag.source_nodes:
            return rag.answer, rag.source_nodes
        print("[HybridQuery] RAG returned no nodes — using QueryOnly answer.")
        return qo.answer, []

    def _fuse_llm_merge(self, query: str, rag: QueryResult, qo: QueryResult):
        """
        Call the LLM to synthesise both answers into one.

        Scaffold: replace the body with a real LLM merge call.
        """
        model = self.planner_config.model
        prompt = (
            f"You received two answers to the question: {query!r}\n\n"
            f"Answer 1 (document-grounded):\n{rag.answer}\n\n"
            f"Answer 2 (general knowledge):\n{qo.answer}\n\n"
            "Synthesise a single, coherent, comprehensive answer."
        )

        print(
            f"[HybridQuery] LLM merge scaffold (model={model!r}). "
            f"Prompt length: {len(prompt)} chars."
        )

        # ── Plug your LLM call here ────────────────────────────────────
        # e.g.:
        #   from openai import OpenAI
        #   client = OpenAI()
        #   resp = client.chat.completions.create(
        #       model=model,
        #       messages=[{"role": "user", "content": prompt}]
        #   )
        #   merged = resp.choices[0].message.content
        #   return merged, rag.source_nodes
        # ──────────────────────────────────────────────────────────────

        # Default fallback: weighted merge
        merged, nodes = self._fuse_weighted(rag, qo)
        return merged, nodes
