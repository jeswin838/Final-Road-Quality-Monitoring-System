from typing import List
from models.hazard import Hazard
from models.reason import Reason

def build_summary(hazard: Hazard, reasons: List[Reason]) -> str:
    """Generates natural language summary."""
    road = getattr(hazard, 'road_name', None) or getattr(hazard, 'road_class', None) or 'Unknown Road'
    pri = getattr(hazard, 'priority', 'Low')
    
    parts = []
    if road and road != "Unknown Road":
        parts.append(f"{pri} hazard detected on {road}.")
    else:
        parts.append(f"{pri} hazard detected.")
        
    for r in reasons:
        parts.append(r.message)
        
    return " ".join(parts)

def build_citizen_message(priority: str) -> str:
    pri = (priority or "").lower()
    if pri == "emergency":
        return "Immediate repair is underway."
    if pri == "critical":
        return "Repair has been prioritised."
    if pri == "high":
        return "Repair has been prioritised."
    if pri == "medium":
        return "Repair has been added to maintenance schedule."
    return "Your report has been recorded."

def build_engineer_message(hazard: Hazard, reasons: List[Reason], actions: List[str]) -> str:
    road = getattr(hazard, 'road_name', None) or getattr(hazard, 'road_class', None) or 'Unknown Road'
    pri = getattr(hazard, 'priority', 'Low')
    
    msg = "Inspection Summary\n\n"
    msg += f"Location:\n{road}\n\n"
    msg += f"Risk:\n{pri}\n\n"
    msg += "Reasons:\n"
    for r in reasons[:4]: # Limit to top 4 for engineer
        msg += f"• {r.message}\n"
        
    msg += "\nRecommended Action:\n"
    for a in actions:
        msg += f"- {a}\n"
        
    return msg

def build_supervisor_message(hazard: Hazard, reasons: List[Reason]) -> str:
    pri = getattr(hazard, 'priority', 'Low')
    msg = "Supervisor attention required because:\n"
    for r in reasons[:3]:
        msg += f"- {r.message}\n"
    msg += f"- Priority {pri}\n"
    return msg
