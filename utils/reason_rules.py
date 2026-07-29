from models.hazard import Hazard
from typing import List, Tuple, Dict, Any

def evaluate_severity(hazard: Hazard) -> List[Dict[str, Any]]:
    sev = (getattr(hazard, 'severity', '') or '').lower()
    if sev == "critical": return [{"code": "R_SEV_01", "confidence": 1.0}]
    if sev == "high": return [{"code": "R_SEV_02", "confidence": 1.0}]
    if sev == "medium": return [{"code": "R_SEV_03", "confidence": 1.0}]
    if sev == "low": return [{"code": "R_SEV_04", "confidence": 1.0}]
    return []

def evaluate_confidence(hazard: Hazard) -> List[Dict[str, Any]]:
    conf = getattr(hazard, 'confidence', 0.0)
    if conf > 0.95: return [{"code": "R_CON_01", "confidence": conf}]
    if conf >= 0.80: return [{"code": "R_CON_02", "confidence": conf}]
    if conf >= 0.60: return [{"code": "R_CON_03", "confidence": conf}]
    return [{"code": "R_CON_04", "confidence": 1.0}]

def evaluate_reports(hazard: Hazard) -> List[Dict[str, Any]]:
    rep = getattr(hazard, 'report_count', 1)
    args = {"count": rep}
    if rep > 20: return [{"code": "R_REP_01", "confidence": 1.0, "args": args}]
    if rep > 10: return [{"code": "R_REP_02", "confidence": 1.0, "args": args}]
    if rep > 5: return [{"code": "R_REP_03", "confidence": 1.0}]
    return [{"code": "R_REP_04", "confidence": 1.0}]

def evaluate_waiting(hazard: Hazard) -> List[Dict[str, Any]]:
    wait = getattr(hazard, 'waiting_days', 0)
    args = {"days": wait}
    if wait > 30: return [{"code": "R_WAT_01", "confidence": 1.0, "args": args}]
    if wait > 14: return [{"code": "R_WAT_02", "confidence": 1.0, "args": args}]
    if wait > 7: return [{"code": "R_WAT_03", "confidence": 1.0}]
    return [{"code": "R_WAT_04", "confidence": 1.0}]

def evaluate_traffic(hazard: Hazard) -> List[Dict[str, Any]]:
    road_class = (getattr(hazard, 'road_class', '') or '').lower()
    if road_class in ["motorway", "national highway", "primary road", "primary"]:
        return [{"code": "R_TRA_01", "confidence": 1.0}]
    return []

def evaluate_road_importance(hazard: Hazard) -> List[Dict[str, Any]]:
    imp = getattr(hazard, 'road_importance', 0) or 0
    road_class = (getattr(hazard, 'road_class', '') or '').lower()
    if imp > 90: return [{"code": "R_IMP_01", "confidence": 1.0}]
    if imp > 70: return [{"code": "R_IMP_02", "confidence": 1.0}]
    if road_class == "residential": return [{"code": "R_IMP_03", "confidence": 1.0}]
    return []

def evaluate_landmarks(hazard: Hazard) -> List[Dict[str, Any]]:
    loc_sum = (getattr(hazard, 'location_summary', '') or '').lower()
    reasons = []
    if "school" in loc_sum: reasons.append({"code": "R_LND_SCHOOL", "confidence": 1.0})
    if "hospital" in loc_sum: reasons.append({"code": "R_LND_HOSPITAL", "confidence": 1.0})
    if "bus" in loc_sum: reasons.append({"code": "R_LND_BUS", "confidence": 1.0})
    if "railway" in loc_sum: reasons.append({"code": "R_LND_RAILWAY", "confidence": 1.0})
    if "college" in loc_sum: reasons.append({"code": "R_LND_COLLEGE", "confidence": 1.0})
    if "market" in loc_sum: reasons.append({"code": "R_LND_MARKET", "confidence": 1.0})
    return reasons

def evaluate_priority(hazard: Hazard) -> List[Dict[str, Any]]:
    pri = (getattr(hazard, 'priority', '') or '').lower()
    if pri == "emergency": return [{"code": "R_PRI_01", "confidence": 1.0}]
    if pri == "critical": return [{"code": "R_PRI_02", "confidence": 1.0}]
    if pri == "high": return [{"code": "R_PRI_03", "confidence": 1.0}]
    if pri == "medium": return [{"code": "R_PRI_04", "confidence": 1.0}]
    if pri == "low": return [{"code": "R_PRI_05", "confidence": 1.0}]
    return []

def evaluate_history_and_clusters(hazard: Hazard) -> List[Dict[str, Any]]:
    reasons = []
    # If history is significantly long
    if hasattr(hazard, 'history') and len(hazard.history) > 3:
        reasons.append({"code": "R_HIS_01", "confidence": 0.9})
        
    # If clustered
    if getattr(hazard, 'cluster_id', None) is not None:
        reasons.append({"code": "R_CLS_01", "confidence": 0.85})
    return reasons
    
def evaluate_operation(hazard: Hazard) -> List[Dict[str, Any]]:
    reasons = []
    m_state = getattr(hazard, 'maintenance_state', '')
    a_state = getattr(hazard, 'assignment_status', '')
    if m_state:
        reasons.append({"code": "R_MNT_STATE", "confidence": 1.0, "args": {"state": m_state}})
    if a_state:
        reasons.append({"code": "R_ASS_STATE", "confidence": 1.0, "args": {"state": a_state}})
    return reasons

def evaluate_all_rules(hazard: Hazard) -> List[Dict[str, Any]]:
    """Returns a combined list of raw reason dictionaries."""
    codes = []
    codes.extend(evaluate_severity(hazard))
    codes.extend(evaluate_confidence(hazard))
    codes.extend(evaluate_reports(hazard))
    codes.extend(evaluate_waiting(hazard))
    codes.extend(evaluate_traffic(hazard))
    codes.extend(evaluate_road_importance(hazard))
    codes.extend(evaluate_landmarks(hazard))
    codes.extend(evaluate_priority(hazard))
    codes.extend(evaluate_history_and_clusters(hazard))
    codes.extend(evaluate_operation(hazard))
    return codes
