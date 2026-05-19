"""
query/executor.py — Output rendering for query results.

The QueryExecutor takes a raw LLM answer + retrieved nodes and renders them
into the format decided by the QueryPlanner (table | chart | form | text),
subject to the ``execution.*`` flags in config.yaml.

Config keys used
----------------
    execution.enable_table : bool
    execution.enable_chart : bool
    execution.enable_form  : bool
    execution.enable_text  : bool
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from query.base import ExecutionConfig, QueryResult


class QueryExecutor:
    """
    Renders a QueryResult into the requested output format.

    Supported formats (when enabled in config):
        table  — structured rows (returns list-of-dicts / DataFrame)
        chart  — chart data dict ready for Plotly / Chart.js
        form   — form schema dict with field definitions
        text   — plain/markdown text (default)
    """

    def __init__(self, execution_config: ExecutionConfig):
        self.config = execution_config

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def render(self, result: QueryResult) -> QueryResult:
        """
        Render ``result.answer`` into the format specified by ``result.output_format``.

        Mutates ``result.rendered`` and returns the same object for chaining.
        If the requested format is disabled, falls back to ``text``.
        """
        fmt = result.output_format.lower()

        # Fall back to text if the requested format is disabled
        if not self._is_enabled(fmt):
            print(
                f"[QueryExecutor] Format '{fmt}' is disabled in config. "
                f"Falling back to 'text'."
            )
            fmt = "text"
            result.output_format = "text"

        dispatcher = {
            "table": self._render_table,
            "chart": self._render_chart,
            "form":  self._render_form,
            "text":  self._render_text,
        }

        render_fn = dispatcher.get(fmt, self._render_text)
        result.rendered = render_fn(result)

        print(
            f"[QueryExecutor] Rendered as '{fmt}' "
            f"(answer_len={len(result.answer)})"
        )
        return result

    # ------------------------------------------------------------------
    # Format renderers
    # ------------------------------------------------------------------

    def _render_text(self, result: QueryResult) -> str:
        """Plain markdown text — returned as-is."""
        return result.answer

    def _render_table(self, result: QueryResult) -> List[Dict[str, Any]]:
        """
        Parse the answer into a list-of-dicts table structure.

        Heuristic: if the answer contains pipe-separated lines (Markdown table),
        parse them; otherwise wrap the full answer in a single-row dict.
        """
        lines = [l.strip() for l in result.answer.splitlines() if l.strip()]

        # Detect Markdown table (lines starting with |)
        table_lines = [l for l in lines if l.startswith("|")]
        if len(table_lines) >= 2:
            return self._parse_markdown_table(table_lines)

        # Detect numbered/bulleted list → convert to rows
        rows = []
        for i, line in enumerate(lines):
            clean = line.lstrip("0123456789.-) ").strip()
            if clean:
                rows.append({"index": i + 1, "content": clean})
        return rows if rows else [{"content": result.answer}]

    def _render_chart(self, result: QueryResult) -> Dict[str, Any]:
        """
        Build a Plotly-compatible chart data dict from the answer.

        Returns a minimal ``{type, data, layout}`` dict.
        Consumers can pass this directly to ``plotly.graph_objects`` or
        ``st.plotly_chart()`` in a Streamlit app.
        """
        # Extract numeric data if present (simple heuristic)
        import re
        numbers = re.findall(r"\b\d+(?:\.\d+)?\b", result.answer)
        labels_raw = re.findall(r"[A-Za-z][A-Za-z\s]{2,20}(?=\s*[:–-]?\s*\d)", result.answer)
        labels = [l.strip() for l in labels_raw] or [f"Item {i+1}" for i in range(len(numbers))]
        values = [float(n) for n in numbers[: len(labels)]]

        return {
            "type": "bar",
            "data": {
                "labels": labels,
                "values": values,
            },
            "layout": {
                "title": result.metadata.get("query", "Query Result"),
                "xaxis": {"title": "Category"},
                "yaxis": {"title": "Value"},
            },
            "raw_answer": result.answer,
        }

    def _render_form(self, result: QueryResult) -> Dict[str, Any]:
        """
        Generate a form schema from the answer.

        Returns a dict with a ``fields`` list, where each field has
        ``name``, ``label``, ``type``, and optional ``required`` flag.
        """
        import re

        fields = []
        # Match patterns like "Field name: description" or numbered items
        pattern = re.compile(
            r"(?:^|\n)\s*(?:\d+[.)]\s*)?([A-Za-z][A-Za-z\s]{1,40})\s*[:–-]\s*(.+)",
            re.MULTILINE,
        )
        for match in pattern.finditer(result.answer):
            label = match.group(1).strip()
            hint = match.group(2).strip()
            field_type = "text"
            if any(k in label.lower() for k in ("date", "time", "when")):
                field_type = "date"
            elif any(k in label.lower() for k in ("email", "mail")):
                field_type = "email"
            elif any(k in label.lower() for k in ("number", "count", "amount", "qty", "quantity")):
                field_type = "number"
            elif any(k in label.lower() for k in ("password", "secret")):
                field_type = "password"

            fields.append({
                "name": label.lower().replace(" ", "_"),
                "label": label,
                "type": field_type,
                "hint": hint,
                "required": False,
            })

        return {
            "title": result.metadata.get("query", "Form"),
            "fields": fields or [{"name": "response", "label": "Response", "type": "text"}],
            "raw_answer": result.answer,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _is_enabled(self, fmt: str) -> bool:
        mapping = {
            "table": self.config.enable_table,
            "chart": self.config.enable_chart,
            "form":  self.config.enable_form,
            "text":  self.config.enable_text,
        }
        return mapping.get(fmt, True)

    @staticmethod
    def _parse_markdown_table(lines: List[str]) -> List[Dict[str, Any]]:
        """Parse a list of Markdown table lines into list-of-dicts."""
        rows = []
        headers: List[str] = []
        for i, line in enumerate(lines):
            cols = [c.strip() for c in line.strip("|").split("|")]
            if i == 0:
                headers = cols
            elif all(set(c) <= set("-: ") for c in cols):
                continue   # separator row
            else:
                rows.append(dict(zip(headers, cols)))
        return rows
