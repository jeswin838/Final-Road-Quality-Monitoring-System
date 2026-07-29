import sqlite3
import json
import logging
from typing import Optional
from models.location import Location

logger = logging.getLogger(__name__)

class GeocoderRepository:
    """Repository for managing the local geocoding cache."""
    
    def __init__(self, db_path: str = "local_db.sqlite"):
        self.db_path = db_path
        self._init_db()
        
    def _get_connection(self):
        return sqlite3.connect(self.db_path)
        
    def _init_db(self):
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS location_cache (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        latitude REAL NOT NULL,
                        longitude REAL NOT NULL,
                        location_data TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                # Index for basic range queries, though distance matching will be done in service
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_location_lat_lon ON location_cache(latitude, longitude)")
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to initialize geocoder repository: {e}")
            
    def save_location(self, location: Location) -> bool:
        """Save a Location object to the cache."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                data = {
                    "road_name": location.road_name,
                    "street": location.street,
                    "village": location.village,
                    "town": location.town,
                    "city": location.city,
                    "district": location.district,
                    "state": location.state,
                    "country": location.country,
                    "postal_code": location.postal_code,
                    "formatted_address": location.formatted_address,
                    "google_maps_url": location.google_maps_url,
                    "road_class": location.road_class,
                    "nearby_place": location.nearby_place,
                    "provider": location.provider,
                    "provider_version": location.provider_version,
                    "cached_at": location.cached_at,
                    "last_verified": location.last_verified,
                    "lookup_time_ms": location.lookup_time_ms,
                    "cache_hit": location.cache_hit,
                    "status": location.status,
                    "road_importance": location.road_importance,
                    "landmark": location.landmark
                }
                cursor.execute(
                    "INSERT INTO location_cache (latitude, longitude, location_data) VALUES (?, ?, ?)",
                    (location.latitude, location.longitude, json.dumps(data))
                )
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error saving location to cache: {e}")
            return False

    def get_all_cached_locations(self) -> list:
        """Fetch all locations for spatial filtering by the service layer."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT latitude, longitude, location_data FROM location_cache")
                rows = cursor.fetchall()
                
                results = []
                for row in rows:
                    lat, lon, data_str = row
                    data = json.loads(data_str)
                    loc = Location(
                        latitude=lat,
                        longitude=lon,
                        **data
                    )
                    results.append(loc)
                return results
        except Exception as e:
            logger.error(f"Error fetching cached locations: {e}")
            return []
