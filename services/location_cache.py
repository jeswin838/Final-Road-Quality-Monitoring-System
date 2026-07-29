import time
import datetime
import math
import logging
from typing import Optional
from models.location import Location
from repositories.geocoder_repository import GeocoderRepository
from config import Config

logger = logging.getLogger(__name__)

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great circle distance in meters between two points on the earth."""
    R = 6371000  # Radius of earth in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * \
        math.sin(delta_lambda / 2.0) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

class LocationCacheService:
    """Service for checking if a location is already cached within a threshold radius."""
    
    def __init__(self):
        self.repository = GeocoderRepository()
        self.cached_dict = {}
        self._load_cache()
        
    def _normalize_coords(self, lat: float, lon: float) -> tuple:
        return (round(float(lat), 6), round(float(lon), 6))
        
    def _load_cache(self):
        """Preload the cache into a dictionary for fast O(1) checks."""
        locations = self.repository.get_all_cached_locations()
        self.cached_dict = {}
        for loc in locations:
            key = self._normalize_coords(loc.latitude, loc.longitude)
            self.cached_dict[key] = loc
            
    def refresh_cache(self):
        """Reload the cache from the database."""
        self._load_cache()

    def get_closest_location(self, latitude: float, longitude: float, threshold_meters: float = None) -> Optional[Location]:
        """Find the exact cached location (O(1) lookup), considering TTL."""
        key = self._normalize_coords(latitude, longitude)
        loc = self.cached_dict.get(key)
        
        if not loc:
            logger.info(f"[GEOCODER] [CACHE MISS] Location {key} not found in cache.")
            return None
            
        # Check TTL
        if loc.cached_at:
            try:
                cached_date = datetime.datetime.fromisoformat(loc.cached_at)
                ttl_days = Config.GEOCODER_CACHE_TTL_DAYS
                now_time = datetime.datetime.now()
                if (now_time - cached_date).days > ttl_days:
                    logger.info(f"[GEOCODER] [CACHE MISS] Location {key} cache expired.")
                    return None
            except:
                pass
                
        loc.cache_hit = True
        logger.info(f"[GEOCODER] [CACHE HIT] Found location in cache for {key}.")
        return loc
        
    def save_location(self, location: Location) -> bool:
        """Save a new location to the cache and update in-memory dict."""
        
        # Any result returned by Geocoder should be marked SUCCESS so we don't repeat lookups
        # Even if it's "Unknown Road", it means the Geocoder doesn't know. No point asking again.
        location.status = "SUCCESS"

        if not location.cached_at:
            location.cached_at = datetime.datetime.now().isoformat()
            
        success = self.repository.save_location(location)
        if success:
            key = self._normalize_coords(location.latitude, location.longitude)
            self.cached_dict[key] = location
            logger.info(f"[GEOCODER] [CACHE] Saved location {key} to cache")
        return success
