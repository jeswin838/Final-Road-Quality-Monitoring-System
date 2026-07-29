from dataclasses import dataclass
from typing import Optional

@dataclass
class WorkflowEvent:
    event_id:   Optional[int]
    task_id:    str
    event_type: str
    event_time: str
    payload:    Optional[str] = None   # JSON string
