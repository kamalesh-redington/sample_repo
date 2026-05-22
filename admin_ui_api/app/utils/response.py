from typing import Any, Optional, Dict, List

from app.config.logger import get_trace_id


def format_response(
    status: str,
    statu_code: Optional[str] = None,
    status_message: Optional[str] = None,
    response: Any = None,
    trace_id: Optional[int] = None,
) -> Dict:
    """Return a consistent API response envelope.

    Keys follow the required output format: `status`, `statu-code`,
    `status-message`, `trace-id`, `response`.
    """
    if trace_id is None:
        ctx = get_trace_id()
        try:
            trace_id = int(ctx) if ctx is not None else None
        except Exception:
            trace_id = ctx

    # ensure response is always a list
    if response is None:
        resp_list: List[Any] = []
    elif isinstance(response, list):
        resp_list = response
    else:
        resp_list = [response]

    return {
        "status": status,
        "statu-code": statu_code or "",
        "status-message": status_message or "",
        "trace-id": trace_id,
        "response": resp_list,
    }
