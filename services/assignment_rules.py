from models.hazard import Hazard
from models.worker import Worker
from typing import List, Tuple, Dict, Any
from services.assignment_score import calculate_assignment_score
from utils.assignment_helpers import calculate_haversine_distance, estimate_travel_time

def is_worker_eligible(worker: Worker) -> bool:
    if (worker.status or "").lower() in ["inactive", "vacation", "suspended"]:
        return False
    if not worker.is_online or worker.is_on_leave:
        return False
    if worker.current_workload >= worker.max_daily_tasks:
        return False
    return True

def determine_required_skill(hazard: Hazard) -> str:
    road_cls = (getattr(hazard, 'road_class', '') or '').lower()
    loc_sum = (getattr(hazard, 'location_summary', '') or '').lower()
    if road_cls == "motorway": return "Highway Maintenance"
    if "bridge" in loc_sum: return "Bridge Division"
    if "drainage" in loc_sum: return "Drainage Team"
    return "General Maintenance"

def determine_required_vehicle(hazard: Hazard) -> str:
    pri = (getattr(hazard, 'priority', '') or '').lower()
    if pri in ["emergency", "critical"]: return "Truck"
    if pri == "low": return "Bike"
    return "Van"
    
def determine_required_equipment(hazard: Hazard) -> List[str]:
    pri = (getattr(hazard, 'priority', '') or '').lower()
    road_cls = (getattr(hazard, 'road_class', '') or '').lower()
    eq = []
    if pri in ["emergency", "critical"]: eq.extend(["Cold Mix", "Warning Cone", "Barrier"])
    if road_cls == "motorway": eq.append("Excavator")
    if not eq: eq.append("Camera")
    return list(set(eq))

def determine_reason(breakdown: Dict[str, float]) -> str:
    # Build a reason string based on what scored highest
    reasons = []
    if breakdown.get("zone", 0) >= 100: reasons.append("Same Zone")
    if breakdown.get("distance", 0) >= 100: reasons.append("Within 2 km")
    if breakdown.get("workload", 0) >= 100: reasons.append("Lowest Workload")
    if breakdown.get("skill", 0) >= 100: reasons.append("Exact Skill Match")
    if breakdown.get("emergency_bonus", 0) > 0: reasons.append("Emergency Responder")
    
    if reasons:
        return ", ".join(reasons)
    return "Best available match."

def evaluate_and_rank_workers(hazard: Hazard, workers: List[Worker]) -> List[Tuple[Worker, float, Dict[str, float]]]:
    # Phase 6b: Zone expansion implicit via scoring
    # Instead of strict filtering, we score all eligible workers and let the score sort them.
    # Same zone = +100, Adjacent = +70, Different = +20
    
    eligible = [w for w in workers if is_worker_eligible(w)]
    req_skill = determine_required_skill(hazard)
    
    scored_workers = []
    for w in eligible:
        total_score, breakdown = calculate_assignment_score(hazard, w, req_skill)
        scored_workers.append((w, total_score, breakdown))
        
    scored_workers.sort(key=lambda x: x[1], reverse=True)
    return scored_workers
