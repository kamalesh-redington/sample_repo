"""
query/planner.py — Rule-based query planner.

The QueryPlanner reads the incoming natural language query and decides:
  1. Which output format to use (table | chart | form | text)
  2. Whether retrieval (RAG) is needed or a direct LLM call suffices
  3. Any query rewrites / decompositions before execution

Config keys used
----------------
    query_planner.model         : LLM model used for planning (e.g. qwen-mini)
    query_planner.rules_enabled : bool — use keyword rules before calling LLM
    execution.*                 : which output formats are allowed
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional

from query.base import ExecutionConfig, QueryPlannerConfig


# ── Planning result ────────────────────────────────────────────────────────────

@dataclass
class PlannerDecision:
    """
    The planner's decision for a single query.

    Attributes:
        output_format:    Preferred rendering format (table|chart|form|text).
        needs_retrieval:  Whether vector-store retrieval is required.
        needs_sql:        Whether SQL execution against relational DB is required.
        rewritten_query:  Optional cleaned/expanded query string.
        sub_queries:      Optional list of decomposed sub-queries (multi-hop).
        reasoning:        Human-readable explanation of the decision.
    """
    output_format: str = "text"
    needs_retrieval: bool = True
    needs_sql: bool = False
    rewritten_query: Optional[str] = None
    sub_queries: List[str] = field(default_factory=list)
    reasoning: str = ""

    def __repr__(self) -> str:
        return (
            f"PlannerDecision(format={self.output_format!r}, "
            f"retrieval={self.needs_retrieval}, sql={self.needs_sql})"
        )


# ── Keyword rule sets ──────────────────────────────────────────────────────────

_TABLE_PATTERNS = [
    r"\b(table|tabular|list|rows?|columns?|compare|comparison|breakdown|summary table)\b",
    r"\b(show me|give me|display|enumerate)\b.*(items?|products?|records?|entries|results)",
]

_CHART_PATTERNS = [
    r"\b(chart|graph|plot|trend|over time|visuali[sz]e|bar|pie|line|histogram)\b",
    r"\b(distribution|growth|decline|percentage|ratio)\b",
]

_FORM_PATTERNS = [
    r"\b(form|fill|input|register|submit|entry|questionnaire)\b",
]

_SQL_PATTERNS = [
    r"\b(how many|count|total|sum|average|avg|max|min|group by|order by|top \d+)\b",
    r"\b(sales|revenue|orders?|transactions?|customers?)\b.*\b(last|this|past)\b.*(week|month|year|quarter)\b",
]

_NO_RETRIEVAL_PATTERNS = [
    r"\b(what is|who is|define|explain briefly|tell me about)\b.{0,40}$",
    r"\b(today'?s? date|current time|what time)\b",
]


def _match_any(text: str, patterns: List[str]) -> bool:
    t = text.lower()
    return any(re.search(p, t) for p in patterns)


# ── Planner ────────────────────────────────────────────────────────────────────

class QueryPlanner:
    """
    Decides output format and retrieval strategy for an incoming query.

    Two operating modes:
        1. Rule-based   — fast regex patterns (when ``rules_enabled=True``)
        2. LLM-assisted — calls ``planner_config.model`` for complex queries
           (currently scaffolded; plug in your LLM client in ``_llm_plan``).
    """

    def __init__(
        self,
        planner_config: QueryPlannerConfig,
        execution_config: ExecutionConfig,
    ):
        self.planner_config = planner_config
        self.execution_config = execution_config
        self._allowed = set(execution_config.enabled_formats())

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def plan(self, query_text: str) -> PlannerDecision:
        """
        Analyse the query and return a PlannerDecision.

        Runs rule-based analysis first (fast + deterministic).
        Falls back to LLM planning if rules don't produce a confident decision.
        """
        if self.planner_config.rules_enabled:
            decision = self._rule_plan(query_text)
            if decision is not None:
                return decision

        return self._llm_plan(query_text)

    # ------------------------------------------------------------------
    # Rule-based planner
    # ------------------------------------------------------------------

    def _rule_plan(self, query_text: str) -> Optional[PlannerDecision]:
        """Apply deterministic keyword rules. Returns None if inconclusive."""
        text = query_text.strip()

        output_format = "text"          # default
        needs_retrieval = True
        needs_sql = False
        reasoning_parts: List[str] = []

        # Detect output format preference
        if "table" in self._allowed and _match_any(text, _TABLE_PATTERNS):
            output_format = "table"
            reasoning_parts.append("table keywords detected")

        elif "chart" in self._allowed and _match_any(text, _CHART_PATTERNS):
            output_format = "chart"
            reasoning_parts.append("chart/visualization keywords detected")

        elif "form" in self._allowed and _match_any(text, _FORM_PATTERNS):
            output_format = "form"
            reasoning_parts.append("form keywords detected")

        else:
            output_format = "text"

        # Detect SQL need
        if _match_any(text, _SQL_PATTERNS):
            needs_sql = True
            reasoning_parts.append("aggregation/SQL keywords detected")

        # Detect if retrieval is needed
        if _match_any(text, _NO_RETRIEVAL_PATTERNS) and len(text) < 80:
            needs_retrieval = False
            reasoning_parts.append("simple factoid — skipping retrieval")

        if not reasoning_parts:
            return None     # rules inconclusive → fall through to LLM

        return PlannerDecision(
            output_format=output_format,
            needs_retrieval=needs_retrieval,
            needs_sql=needs_sql,
            rewritten_query=text,
            reasoning="; ".join(reasoning_parts),
        )

    # ------------------------------------------------------------------
    # LLM-assisted planner (scaffold)
    # ------------------------------------------------------------------

    def _llm_plan(self, query_text: str) -> PlannerDecision:
        """
        Call the configured planner model for complex routing decisions.

        Scaffold: replace the body of this method with your LLM client call.
        The model should return a JSON object matching PlannerDecision fields.

        Example prompt structure::

            system: You are a query router. Respond ONLY as JSON with keys:
                    output_format, needs_retrieval, needs_sql, reasoning.
            user:   Query: "{query_text}"
                    Allowed formats: {allowed_formats}
        """
        model = self.planner_config.model
        print(
            f"[QueryPlanner] LLM planning via model={model!r} "
            f"(rules found no match for query length={len(query_text)})"
        )

        # ── Plug your LLM call here ────────────────────────────────────
        # e.g.:
        #   from openai import OpenAI
        #   client = OpenAI()
        #   resp = client.chat.completions.create(model=model, messages=[...])
        #   parsed = json.loads(resp.choices[0].message.content)
        #   return PlannerDecision(**parsed)
        # ──────────────────────────────────────────────────────────────

        # Default fallback until LLM is wired in
        return PlannerDecision(
            output_format="text" if "text" in self._allowed else list(self._allowed)[0],
            needs_retrieval=True,
            reasoning=f"LLM planner scaffold (model={model!r}); defaulting to text+retrieval",
        )
