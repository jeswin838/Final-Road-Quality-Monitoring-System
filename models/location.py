from dataclasses import dataclass
from typing import Optional

@dataclass
class Location:
    latitude: float
    longitude: float
    road_name: str = "Unknown Road"
    street: str = ""
    village: str = ""
    hamlet: str = ""
    neighbourhood: str = ""
    suburb: str = ""
    town: str = ""
    city: str = ""
    district: str = "Unknown"
    state: str = ""
    country: str = ""
    postal_code: str = ""
    formatted_address: str = "Location unavailable"
    google_maps_url: str = ""
    road_class: str = "Unknown"
    nearby_place: str = ""
    
    # Enterprise fields
    provider: str = ""
    provider_version: str = ""
    cached_at: str = ""
    last_verified: str = ""
    lookup_time_ms: int = 0
    cache_hit: bool = False
    status: str = "PENDING"
    road_importance: int = 10
    traffic_importance: str = "Unknown"
    landmark: str = "Unavailable"
