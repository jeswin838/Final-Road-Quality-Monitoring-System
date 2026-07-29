from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class TimelineItem:
    timestamp:  str
    state:      str
    actor:      str
    actor_type: str
    message:    str
    image:      Optional[str] = None
    gps_lat:    Optional[float] = None
    gps_lon:    Optional[float] = None
    device:     Optional[str] = None
    remarks:    Optional[str] = None


@dataclass
class MaintenanceTimeline:
    task_id:        str
    items:          List[TimelineItem] = field(default_factory=list)
    total_duration: Optional[float] = None   # minutes from created to closed
