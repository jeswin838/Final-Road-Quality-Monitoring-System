from utils.priority_constants import (
    ROAD_PRIORITY, TRAFFIC_PRIORITY, WAITING_BONUS_MAX_DAYS, REPORT_BONUS_MAX_COUNT, EMERGENCY_BONUS
)
from models.hazard import Hazard

def calculate_road_priority(road_importance: int) -> int:
    sorted_tiers = sorted(ROAD_PRIORITY.keys(), reverse=True)
    if not road_importance:
        return ROAD_PRIORITY[10]
    for tier in sorted_tiers:
        if road_importance >= tier:
            return ROAD_PRIORITY[tier]
    return ROAD_PRIORITY[10]

def calculate_traffic_priority(road_class: str) -> int:
    return TRAFFIC_PRIORITY.get(road_class or "Unknown", TRAFFIC_PRIORITY["Unknown"])

def calculate_waiting_priority(waiting_days: int) -> int:
    days = waiting_days or 0
    # Saturating function: 90 days = 100% priority.
    # We can use min(100, (days / 90) * 100) or a curve.
    return int(min(100, max(0, (days / 90.0) * 100)))

def calculate_report_priority(report_count: int) -> int:
    count = report_count or 1
    if count <= 1:
        return 0
    import math
    # Logarithmic scale: 1 -> 0, 10 -> 40, 100 -> 80, 316+ -> 100
    return int(min(100, max(0, math.log10(count) * 40)))

def calculate_severity_priority(severity: str) -> int:
    sev = str(severity).lower()
    if sev == "critical":
        return 100
    elif sev == "high":
        return 80
    elif sev == "medium":
        return 55
    elif sev == "low":
        return 30
    return 30

def calculate_emergency_priority(hazard: Hazard) -> int:
    if getattr(hazard, 'requires_emergency_team', False):
        return EMERGENCY_BONUS
    return 0

def determine_escalation_level(hazard: Hazard) -> int:
    if getattr(hazard, 'risk_score', 0) > 95:
        return 5
    if getattr(hazard, 'requires_road_closure', False):
        return 4
    if getattr(hazard, 'is_repeated_location', False):
        return 3
    if getattr(hazard, 'waiting_days', 0) > 30:
        return 2
    return 1

def generate_priority_reason(hazard: Hazard) -> str:
    reasons = []
    
    # Repeated citizen complaints detected.
    if getattr(hazard, 'is_repeated_location', False):
        reasons.append("Repeated citizen complaints detected.")
        
    # Large pothole on State Highway. / Heavy traffic road. / Low traffic residential road.
    severity_str = (getattr(hazard, 'severity', '') or "unknown").lower()
    road_cls = getattr(hazard, 'road_class', 'Unknown Road')
    
    if getattr(hazard, 'is_high_traffic', False):
        reasons.append(f"{severity_str.capitalize()} hazard on heavy traffic road ({road_cls}).")
    elif (road_cls or "").lower() in ["residential", "local road"]:
        reasons.append(f"Low traffic {(road_cls or '').lower()}.")
    else:
        reasons.append(f"{severity_str.capitalize()} hazard on {road_cls}.")
        
    # Repair instructions
    repair_cat = getattr(hazard, 'repair_category', '')
    if "Immediate" in repair_cat:
        reasons.append("Repair immediately.")
    elif "24" in repair_cat or "48" in repair_cat or "7" in repair_cat:
        reasons.append(f"Repair within {repair_cat}.")
    else:
        reasons.append("Schedule in next maintenance cycle.")
        
    return " ".join(reasons)
