from models.hazard import Hazard
from typing import Optional

def resolve_target_team_type(hazard: Hazard) -> Optional[str]:
    """Determines the specific team required based on hazard properties."""
    if getattr(hazard, 'requires_emergency_team', False):
        return "EMERGENCY"
    
    if getattr(hazard, 'requires_contract_team', False):
        return "CONTRACTOR"
        
    road_cls = getattr(hazard, 'road_class', '').upper()
    if "HIGHWAY" in road_cls or "MOTORWAY" in road_cls:
        return "HIGHWAY"
        
    if getattr(hazard, 'requires_municipality', False):
        return "MUNICIPALITY"
        
    return "ROAD_MAINTENANCE"
