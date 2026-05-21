from pathlib import Path
from typing import Union
from config.logger import setup_logger
from config.timer import log_execution_time

logger = setup_logger(__name__)

PathLike = Union[str, Path]


@log_execution_time(logger)
def ensure_dir(path: PathLike) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p
