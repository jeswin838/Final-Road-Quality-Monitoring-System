from utils.risk_constants import (
    SEVERITY_WEIGHTS, get_confidence_weight, get_report_weight,
    get_age_weight, ROAD_WEIGHTS, TRAFFIC_WEIGHTS
)
import datetime

def calculate_severity_score(severity: str) -> int:
    return SEVERITY_WEIGHTS.get((severity or "").lower(), SEVERITY_WEIGHTS["unknown"])

def calculate_confidence_score(confidence: float) -> int:
    return get_confidence_weight(confidence or 0.0)

def calculate_report_score(report_count: int) -> int:
    return get_report_weight(report_count or 1)

def calculate_waiting_days(created_at: str) -> int:
    if not created_at:
        return 0
    try:
        dt = datetime.datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        # Use timezone naive diff for simplicity assuming local or UTC
        now = datetime.datetime.now(dt.tzinfo) if dt.tzinfo else datetime.datetime.now()
        days = (now - dt).days
        return max(0, days)
    except Exception:
        return 0

def calculate_age_score(waiting_days: int) -> int:
    return get_age_weight(waiting_days)

def calculate_road_score(road_importance: int) -> int:
    # Match the exact or closest lower tier
    sorted_tiers = sorted(ROAD_WEIGHTS.keys(), reverse=True)
    if not road_importance:
        return ROAD_WEIGHTS[10]
    for tier in sorted_tiers:
        if road_importance >= tier:
            return ROAD_WEIGHTS[tier]
    return ROAD_WEIGHTS[10]

def calculate_traffic_score(road_class: str) -> int:
    return TRAFFIC_WEIGHTS.get(road_class or "Unknown", TRAFFIC_WEIGHTS["Unknown"])

def generate_reason(hazard) -> str:
    reasons = []
    
    if hazard.is_repeated_location:
        reasons.append("Repeated complaints detected.")
        
    if hazard.confidence_score >= 15:
        reasons.append("High confidence AI detection.")
        
    if hazard.road_class in ["Motorway", "National Highway", "Primary"]:
        reasons.append(f"Located on {(hazard.road_class or '').lower()}.")
        
    if hazard.waiting_days and hazard.waiting_days > 0:
        reasons.append(f"Waiting {hazard.waiting_days} days.")
        
    if hazard.severity_score >= SEVERITY_WEIGHTS["high"]:
        reasons.append("Severe surface damage.")
        
    return " ".join(reasons) if reasons else "Routine hazard detection."

def generate_action(hazard) -> str:
    if hazard.requires_emergency_team:
        return "Emergency repair required. Dispatch team immediately."
    elif hazard.requires_assignment and hazard.requires_supervisor:
        return "Escalate to supervisor and assign repair team immediately."
    elif hazard.requires_assignment:
        return "Assign repair team immediately."
    elif hazard.risk_level == "Medium":
        return "Schedule maintenance."
    else:
        return "Monitor location."
