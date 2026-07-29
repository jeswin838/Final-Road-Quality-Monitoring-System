from models.hazard import Hazard
from typing import Dict, Any

def generate_recommendations(hazard: Hazard) -> Dict[str, Any]:
    pri = (getattr(hazard, 'priority', '') or '').lower()
    road_cls = (getattr(hazard, 'road_class', '') or '').lower()
    
    rec = {
        "team": "Inspection Team",
        "skill": "Inspection",
        "vehicle": "Standard Van",
        "equipment": ["Camera", "Tablet"]
    }
    
    if pri == "emergency":
        rec["team"] = "Emergency Team"
        rec["skill"] = "Emergency Repair"
        rec["vehicle"] = "Emergency Response Truck"
        rec["equipment"] = ["Cold Asphalt", "Traffic Barriers", "Warning Lights"]
        
    elif "highway" in road_cls or "motorway" in road_cls:
        rec["team"] = "Highway Team"
        rec["skill"] = "Highway Maintenance"
        rec["vehicle"] = "Heavy Duty Truck"
        rec["equipment"] = ["Traffic Barriers", "Heavy Equipment"]
        
    elif getattr(hazard, 'requires_contract_team', False):
        rec["team"] = "Contract Team"
        rec["skill"] = "General Repair"
        rec["vehicle"] = "Contractor Van"
        
    elif getattr(hazard, 'requires_municipality', False):
        rec["team"] = "Municipality Team"
        rec["skill"] = "Local Maintenance"
        rec["vehicle"] = "Municipal Truck"
        rec["equipment"] = ["Cold Asphalt"]
        
    return rec
