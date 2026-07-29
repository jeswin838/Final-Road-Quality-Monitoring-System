from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class AssignmentRecommendation:
    worker_id: str
    worker_name: str
    recommended_team: str
    recommended_vehicle: str
    recommended_equipment: List[str]
    recommended_eta: float
    recommended_distance: float
    recommendation_score: float
    score_breakdown: Dict[str, float]
    recommendation_reason: str

@dataclass
class AssignmentRecommendationBundle:
    hazard_id: str
    recommendations: List[AssignmentRecommendation]
    engine_version: str
    generated_time: str
