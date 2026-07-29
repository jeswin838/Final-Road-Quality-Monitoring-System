from models.hazard import Hazard
from models.worker import Worker
from typing import Dict, Tuple
from utils.assignment_constants import *
from utils.assignment_helpers import calculate_haversine_distance

def calculate_assignment_score(hazard: Hazard, worker: Worker, required_skill: str) -> Tuple[float, Dict[str, float]]:
    breakdown = {
        "availability": 0.0,
        "zone": 0.0,
        "distance": 0.0,
        "workload": 0.0,
        "skill": 0.0,
        "priority": 0.0,
        "emergency_bonus": 0.0
    }
    
    # Availability
    if not worker.is_online or worker.is_on_leave:
        breakdown["availability"] = SCORE_AVAILABILITY_OFFLINE
    elif worker.current_workload >= worker.max_daily_tasks:
        breakdown["availability"] = SCORE_AVAILABILITY_BUSY
    else:
        breakdown["availability"] = SCORE_AVAILABILITY_AVAILABLE
        
    # Zone
    h_zone = getattr(hazard, 'zone', 'Unknown')
    if h_zone == worker.zone:
        breakdown["zone"] = SCORE_ZONE_SAME
    elif getattr(hazard, 'district', '') == worker.district:
        breakdown["zone"] = SCORE_ZONE_ADJACENT
    else:
        breakdown["zone"] = SCORE_ZONE_DIFFERENT
        
    # Distance
    h_lat = getattr(hazard, 'latitude', 0.0)
    h_lng = getattr(hazard, 'longitude', 0.0)
    
    if h_lat and h_lng and worker.latitude and worker.longitude:
        dist = calculate_haversine_distance(h_lat, h_lng, worker.latitude, worker.longitude)
        if dist <= 2.0:
            breakdown["distance"] = SCORE_DISTANCE_CLOSE
        elif dist <= 5.0:
            breakdown["distance"] = SCORE_DISTANCE_MEDIUM
        else:
            breakdown["distance"] = SCORE_DISTANCE_FAR
    else:
        breakdown["distance"] = SCORE_DISTANCE_FAR
        
    # Workload
    wl = worker.current_workload
    if wl == 0:
        breakdown["workload"] = SCORE_WORKLOAD_EMPTY
    elif wl <= 2:
        breakdown["workload"] = SCORE_WORKLOAD_LIGHT
    else:
        breakdown["workload"] = SCORE_WORKLOAD_HEAVY
        
    # Skill Match
    if required_skill in worker.skills:
        breakdown["skill"] = SCORE_SKILL_EXACT
    elif "General Maintenance" in worker.skills:
        breakdown["skill"] = SCORE_SKILL_GENERAL
    else:
        breakdown["skill"] = SCORE_SKILL_PARTIAL
        
    # Priority Base
    pri = (getattr(hazard, 'priority', 'Low') or '').lower()
    if pri == "emergency": breakdown["priority"] = SCORE_PRIORITY_EMERGENCY
    elif pri == "critical": breakdown["priority"] = SCORE_PRIORITY_CRITICAL
    elif pri == "high": breakdown["priority"] = SCORE_PRIORITY_HIGH
    elif pri == "medium": breakdown["priority"] = SCORE_PRIORITY_MEDIUM
    else: breakdown["priority"] = SCORE_PRIORITY_LOW
    
    # Bonuses
    if pri == "emergency" or worker.is_emergency_team: 
        breakdown["emergency_bonus"] += BONUS_EMERGENCY
    loc_sum = (getattr(hazard, 'location_summary', '') or '').lower()
    if "school" in loc_sum: breakdown["emergency_bonus"] += BONUS_SCHOOL
    if "hospital" in loc_sum: breakdown["emergency_bonus"] += BONUS_HOSPITAL
    road_cls = (getattr(hazard, 'road_class', '') or '').lower()
    if road_cls == "motorway": breakdown["emergency_bonus"] += BONUS_MOTORWAY
    
    total_score = sum(breakdown.values())
    
    return total_score, breakdown
