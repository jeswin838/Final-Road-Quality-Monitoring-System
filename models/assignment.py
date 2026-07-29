from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class Assignment:
    assignment_id: str
    hazard_id: str
    worker_id: str
    recommended_team: str
    recommended_vehicle: str
    recommended_equipment: List[str] = field(default_factory=list)
    recommended_eta: float = 0.0
    recommended_distance: float = 0.0
    recommendation_score: float = 0.0
    score_breakdown: Dict[str, float] = field(default_factory=dict)
    recommendation_reason: str = ""
    approved_by_admin: bool = False
    assigned_time: Optional[str] = None
    accepted_at: Optional[str] = None
    travel_start: Optional[str] = None
    repair_start: Optional[str] = None
    repair_completed: Optional[str] = None
    verification_completed: Optional[str] = None
    status: str = "Recommended"
    estimated_completion: Optional[str] = None
    priority: str = "Low"
    history: List[str] = field(default_factory=list)
