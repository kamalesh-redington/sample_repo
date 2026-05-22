from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from config.logger import trace_id_ctx


class StandardResponseModel(BaseModel):
    status: str
    statu_code: str = Field(..., alias="statu-code")
    status_message: str = Field(..., alias="status-message")
    trace_id: str = Field(..., alias="trace-id")
    response: List[Any] = Field(default_factory=list)

    class Config:
        allow_population_by_field_name = True
        allow_mutation = True


def format_response(
    status: str,
    statu_code: Optional[str] = "",
    status_message: Optional[str] = "",
    response: Optional[Any] = None,
    trace_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Return a standardized API response dict.

    Always returns the following structure:

    {
        "status": "",
        "statu-code": "",
        "status-message": "",
        "trace-id": "",
        "response": {}
    }

    The function will attempt to read the current request `trace_id` from
    `config.logger.trace_id_ctx` when `trace_id` is not explicitly provided.
    """

    # Ensure response is always a list per project requirement
    if response is None:
        response_list: List[Any] = []
    else:
        # if the response is already a list, use it; otherwise wrap single object in a list
        if isinstance(response, list):
            response_list = response
        else:
            response_list = [response]

    if trace_id is None:
        try:
            trace_id = trace_id_ctx.get()
        except Exception:
            trace_id = "-"

    return {
        "status": status,
        "statu-code": str(statu_code) if statu_code is not None else "",
        "status-message": status_message if status_message is not None else "",
        "trace-id": trace_id,
        "response": response_list,
    }
