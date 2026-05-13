"""
query/providers/rag_query.py

Strategy: ``rag``

Classic RAG pipeline:
  1. QueryPlanner decides output format and whether retrieval is needed.
  2. Retrieve top-k chunks from the vector index.
  3. Build a context-augmented prompt.
  4. Call the LLM for the final answer.
  5. QueryExecutor renders the answer into table | chart | form | text.
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


class RAGQuery(BaseQueryStrategy):
    """
    Retrieval-Augmented Generation query strategy.

    Retrieves relevant chunks from the vector index, assembles them as
    context, then calls the LLM to answer the query.

    Config used
    -----------
        query_mode.strategy      : rag
        query_planner.model      : LLM model for answer generation
        query_planner.rules_enabled : whether to use rule-based planner
        execution.*              : controls output rendering format
        query/db_config.yaml → vector_db.query.top_k  (default 10)
        query/db_config.yaml → vector_db.query.score_threshold (default 0.70)
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

    def execute(self, query_text: str, index: Any, **kwargs) -> QueryResult:
        """
        Execute a RAG query.

        Args:
            query_text: Natural language query.
            index:      LlamaIndex VectorStoreIndex (or compatible retriever).
            **kwargs:   Optional overrides:
                        - top_k (int): override db_config top_k
                        - similarity_top_k (int): alias for top_k

        Returns:
            QueryResult with answer, source_nodes, and rendered output.
        """
        print(f"[RAGQuery] Executing RAG query: {query_text[:80]!r}...")

        # Step 1 — Query planning
        decision = self._planner.plan(query_text)
        print(f"[RAGQuery] Planner decision: {decision}")

        # Step 2 — Retrieve
        top_k = kwargs.get("top_k") or kwargs.get("similarity_top_k")
        if top_k is None and self.db_config:
            top_k = self.db_config.vector_db.get("query", {}).get("top_k", 10)
        top_k = int(top_k or 10)

        effective_query = decision.rewritten_query or query_text
        source_nodes = self._retrieve(index, effective_query, top_k)

        # Step 3 — Build context
        context = self._build_context(source_nodes)

        # Step 4 — Generate answer
        answer = self._generate_answer(
            query=effective_query,
            context=context,
            model=self.planner_config.model,
        )

        # Step 5 — Render
        result = QueryResult(
            answer=answer,
            strategy="rag",
            source_nodes=source_nodes,
            output_format=decision.output_format,
            metadata={
                "query": query_text,
                "rewritten_query": decision.rewritten_query,
                "top_k": top_k,
                "planner_reasoning": decision.reasoning,
            },
        )
        return self._executor.render(result)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _retrieve(index: Any, query_text: str, top_k: int):
        """Call the index retriever and return source nodes."""
        try:
            retriever = index.as_retriever(similarity_top_k=top_k)
            return retriever.retrieve(query_text)
        except Exception as exc:
            print(f"[RAGQuery] Retrieval error: {exc}")
            return []

    @staticmethod
    def _build_context(source_nodes) -> str:
        """Concatenate retrieved node texts into a context string."""
        if not source_nodes:
            return ""
        parts = []
        for i, node in enumerate(source_nodes, 1):
            text = getattr(node, "text", str(node))
            parts.append(f"[{i}] {text}")
        return "\n\n".join(parts)

    @staticmethod
    def _generate_answer(query: str, context: str, model: str) -> str:
        """
        Generate the LLM answer.

        Scaffold: plug your LLM client call here.
        Currently uses the LlamaIndex query engine path when context is available.
        """
        if not context:
            return f"No relevant context found for query: {query!r}"

        # ── Plug your LLM call here ────────────────────────────────────
        # Example (OpenAI):
        #   from openai import OpenAI
        #   client = OpenAI()
        #   prompt = f"Context:\n{context}\n\nQuestion: {query}\nAnswer:"
        #   resp = client.chat.completions.create(
        #       model=model,
        #       messages=[{"role": "user", "content": prompt}]
        #   )
        #   return resp.choices[0].message.content
        # ──────────────────────────────────────────────────────────────

        # Default: return context as answer (replace with real LLM call)
        print(
            f"[RAGQuery] LLM call scaffold (model={model!r}). "
            f"Context length: {len(context)} chars."
        )
        return f"[LLM:{model}] Based on {len(context)} chars of context:\n\n{context[:500]}..."
