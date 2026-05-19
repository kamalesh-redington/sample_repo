"""
query — config-driven query execution module.

Public API
----------
    from query.factory import QueryFactory

    strategy = QueryFactory.create(config)
    result   = strategy.execute(query_text, index)

Available strategies (config.query_mode.strategy)
-------------------------------------------------
    rag         → RAGQuery       vector retrieval → LLM answer
    query_only  → QueryOnlyQuery direct LLM query (no retrieval)
    hybrid      → HybridQuery    rag + query_only merged result

Components
----------
    QueryFactory   — registry-based factory (reads query_mode.strategy)
    QueryPlanner   — rule-based planner (reads query_planner config)
    QueryExecutor  — renders output as table | chart | form | text
    QueryDbConfig  — loads query/db_config.yaml
"""

__all__ = ["QueryFactory", "QueryPlanner", "QueryExecutor", "QueryDbConfig"]
