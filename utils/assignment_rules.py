from models.hazard import Hazard
from models.worker import Worker
from utils.assignment_constants import ASSIGNMENT_WEIGHTS
from utils.workload_rules import calculate_workload_penalty

def calculate_distance_score(hazard_lat: float, hazard_lon: float, worker_lat: float, worker_lon: float) -> float:
    """Mock distance score. In production, use Haversine or GIS routing."""
    # Assuming lower distance = higher score, mock 100 for now.
    return 80.0

def calculate_skill_match(hazard: Hazard, worker: Worker) -> float:
    """Scores worker skills against hazard requirements."""
    score = 0.0
    if getattr(hazard, 'requires_emergency_team', False) and "Emergency" in worker.skills:
        score += 50.0
    if getattr(hazard, 'requires_contract_team', False) and "Highway" in worker.skills:
        score += 50.0
    road_class = getattr(hazard, 'road_class', '')
    if road_class in worker.road_types:
        score += 50.0
    return min(100.0, score)

def calculate_zone_match(hazard: Hazard, worker: Worker) -> float:
    """Scores zone matching. Prefer local workers."""
    h_zone = getattr(hazard, 'zone', '')
    w_zone = worker.zone
    if h_zone and h_zone == w_zone:
        return 100.0
    return 0.0

def calculate_assignment_score(hazard: Hazard, worker: Worker) -> float:
    """Calculates the total assignment score for a worker-hazard pairing."""
    priority_score = getattr(hazard, 'priority_score', 0)
    
    # Distance mock
    distance_score = calculate_distance_score(hazard.latitude, hazard.longitude, worker.current_location.get("lat", 0), worker.current_location.get("lon", 0))
    
    availability_score = 100.0 if worker.status == "Available" else 50.0 if worker.status == "Travelling" else 0.0
    
    capacity_score = 100.0 if worker.current_capacity < worker.maximum_capacity else 0.0
    
    skill_score = calculate_skill_match(hazard, worker)
    zone_score = calculate_zone_match(hazard, worker)
    
    workload_penalty = calculate_workload_penalty(worker)
    
    total = (
        (priority_score * ASSIGNMENT_WEIGHTS["priority"]) +
        (distance_score * ASSIGNMENT_WEIGHTS["distance"]) +
        (availability_score * ASSIGNMENT_WEIGHTS["availability"]) +
        (capacity_score * ASSIGNMENT_WEIGHTS["capacity"]) +
        (skill_score * ASSIGNMENT_WEIGHTS["skill_match"]) +
        (zone_score * ASSIGNMENT_WEIGHTS["zone_match"]) -
        (workload_penalty * ASSIGNMENT_WEIGHTS["workload_penalty"])
    )
    
    return max(0.0, total)
