import math

def calculate_haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Returns distance in kilometers using the Haversine formula."""
    R = 6371.0 # Earth radius in km

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c

def estimate_travel_time(distance_km: float) -> float:
    """Returns travel time in hours. Assuming 30 km/h average speed in city."""
    return distance_km / 30.0

def estimate_repair_duration(priority: str) -> float:
    """Returns repair duration in hours based on priority."""
    p = priority.lower()
    if p == "emergency": return 4.0
    if p == "critical": return 8.0
    if p == "high": return 24.0
    return 48.0
