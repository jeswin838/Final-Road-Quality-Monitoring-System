from models.hazard import Hazard
from typing import List

def generate_recommended_actions(hazard: Hazard) -> List[str]:
    pri = (getattr(hazard, 'priority', '') or '').lower()
    actions = []
    
    if pri == "emergency":
        actions.extend(["Deploy traffic cones", "Assign emergency repair team", "Road closure may be required"])
    elif pri == "critical":
        actions.extend(["Assign emergency repair crew", "Escalate to supervisor", "Verify repair"])
    elif pri == "high":
        actions.extend(["Notify municipality", "Schedule inspection", "Upload completion photo"])
    else:
        actions.extend(["Monitor location", "Verify after repair"])
        
    return actions
