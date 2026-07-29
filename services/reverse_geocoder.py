import time
import requests
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Dict, Any
from models.location import Location
from services.location_cache import LocationCacheService
from services.photon_service import PhotonService
from services.overpass_service import OverpassService
from config import Config
from utils.rate_limiter import RateLimiter
from utils.geocoder_retry import GeocoderRetryEngine
import datetime

logger = logging.getLogger(__name__)

class ReverseGeocoderService:
    """Enterprise Reverse Geocoder with Provider Dispatcher, Queue, and Retry Engine."""
    
    def __init__(self):
        self.cache_service = LocationCacheService()
        self.executor = ThreadPoolExecutor(max_workers=Config.GEOCODER_WORKERS)
        self.fetch_executor = ThreadPoolExecutor(max_workers=15)
        self.rate_limiter = RateLimiter(calls_per_second=1.0)
        self.headers = {"User-Agent": Config.GEOCODER_USER_AGENT}
        
    def _calculate_road_importance(self, road_class: str) -> int:
        rc = str(road_class).lower()
        importances = {
            'motorway': 95,
            'trunk': 90,
            'primary': 80,
            'secondary': 70,
            'tertiary': 60,
            'residential': 40,
            'living_street': 30,
            'service': 20,
            'track': 10,
            'path': 10,
            'footway': 10,
            'cycleway': 10,
            'pedestrian': 10,
            'construction': 10,
            'road': 10
        }
        return importances.get(rc, 10)

    def _calculate_traffic_importance(self, road_class: str) -> str:
        rc = str(road_class).lower()
        if rc in ['motorway', 'trunk']: return "Very High"
        if rc == 'primary': return "High"
        if rc in ['secondary', 'tertiary']: return "Medium"
        if rc in ['residential', 'living_street']: return "Low"
        if rc == 'service': return "Very Low"
        if rc in ['track', 'path', 'footway', 'cycleway', 'pedestrian']: return "Minimal"
        return "Unknown"

    def _build_formatted_address(self, loc: Location) -> str:
        parts = []
        if getattr(loc, 'road_name', '') and loc.road_name != "Unnamed Road": parts.append(loc.road_name)
        if getattr(loc, 'street', '') and getattr(loc, 'street') != getattr(loc, 'road_name') and loc.street != "Unnamed Road": parts.append(loc.street)
        if getattr(loc, 'landmark', '') and loc.landmark != "No Nearby Landmark": parts.append(loc.landmark)
        if getattr(loc, 'village', '') and loc.village != "Village Not Available": parts.append(loc.village)
        if getattr(loc, 'town', '') and loc.town != "Town Not Available": parts.append(loc.town)
        if getattr(loc, 'district', '') and loc.district != "District Not Available": parts.append(loc.district)
        if getattr(loc, 'state', '') and loc.state != "State Not Available": parts.append(loc.state)
        if getattr(loc, 'country', '') and loc.country != "Country Not Available": parts.append(loc.country)
        
        seen = set()
        unique_parts = []
        for p in parts:
            if p not in seen:
                seen.add(p)
                unique_parts.append(p)
                
        return ",\n".join(unique_parts) if unique_parts else "Location Not Available"

    def _safe_str(self, val: str, fallback: str) -> str:
        if not val or str(val).strip().lower() in ["", "none", "null", "unknown", "unknown road", "unavailable"]:
            return fallback
        return str(val).strip()

    def _fetch_nominatim_raw(self, latitude: float, longitude: float) -> dict:
        self.rate_limiter.wait()
        params = {
            'lat': latitude,
            'lon': longitude,
            'format': 'json',
            'addressdetails': 1,
            'extratags': 1,
            'namedetails': 1
        }
        try:
            response = requests.get(Config.NOMINATIM_URL, params=params, headers=self.headers, timeout=5)
            if response.status_code == 200:
                return response.json()
        except:
            pass
        return {}

    def _fetch_photon_raw(self, latitude: float, longitude: float) -> dict:
        try:
            return PhotonService.query(latitude, longitude)
        except:
            return {}
            
    def _fetch_overpass_raw(self, latitude: float, longitude: float) -> dict:
        try:
            return OverpassService.query(latitude, longitude)
        except:
            return {}

    def _fetch_location(self, latitude: float, longitude: float, existing_cache: Optional[Location] = None) -> Location:
        start_time = time.time()
        
        future_nom = self.fetch_executor.submit(self._fetch_nominatim_raw, latitude, longitude)
        future_pho = self.fetch_executor.submit(self._fetch_photon_raw, latitude, longitude)
        future_ovp = self.fetch_executor.submit(self._fetch_overpass_raw, latitude, longitude)
        
        nom_data = {}
        pho_data = {}
        ovp_data = {}
        
        try: nom_data = future_nom.result(timeout=6)
        except: pass
        try: pho_data = future_pho.result(timeout=6)
        except: pass
        try: ovp_data = future_ovp.result(timeout=6)
        except: pass
            
        nom_addr = nom_data.get('address', {})
        
        # Extracted variables
        nom_road_raw = nom_addr.get('road', '')
        pho_road_raw = pho_data.get('street', '') or pho_data.get('road', '')
        ovp_road_raw = ovp_data.get('highway_name', '')
        cache_road = getattr(existing_cache, 'road_name', '') if existing_cache else ''
        
        nom_class_raw = nom_data.get('type', '') if nom_data.get('category') == 'highway' else nom_addr.get('highway', '')
        ovp_class_raw = ovp_data.get('highway_class', '')
        cache_class = getattr(existing_cache, 'road_class', '') if existing_cache else ''
        
        ovp_lm_raw = ovp_data.get('landmark', '')
        nom_lm_raw = ""
        for k in ['hospital', 'clinic', 'school', 'college', 'temple', 'church', 'mosque', 'railway_station', 'bus_stop', 'airport', 'mall', 'park']:
            if nom_addr.get(k):
                nom_lm_raw = nom_addr[k]
                break
        cache_lm = getattr(existing_cache, 'landmark', '') if existing_cache else ''
        
        pho_village_raw = pho_data.get('village') or pho_data.get('hamlet') or pho_data.get('suburb') or pho_data.get('quarter')
        nom_village_raw = nom_addr.get('village') or nom_addr.get('hamlet') or nom_addr.get('suburb') or nom_addr.get('quarter')
        ovp_village_raw = ovp_data.get('place_name', '') if ovp_data.get('place_type') in ['village', 'hamlet', 'suburb'] else ''
        cache_village = getattr(existing_cache, 'village', '') if existing_cache else ''
        
        pho_town_raw = pho_data.get('town') or pho_data.get('city') or pho_data.get('municipality')
        nom_town_raw = nom_addr.get('town') or nom_addr.get('city') or nom_addr.get('municipality')
        cache_town = getattr(existing_cache, 'town', '') if existing_cache else ''
        
        nom_district_raw = nom_addr.get('state_district') or nom_addr.get('county')
        pho_district_raw = pho_data.get('district', '')
        cache_district = getattr(existing_cache, 'district', '') if existing_cache else ''
        
        pho_state_raw = pho_data.get('state', '')
        nom_state_raw = nom_addr.get('state', '')
        cache_state = getattr(existing_cache, 'state', '') if existing_cache else ''
        
        pho_country_raw = pho_data.get('country', '')
        nom_country_raw = nom_addr.get('country', '')
        cache_country = getattr(existing_cache, 'country', '') if existing_cache else ''
        
        def safe_val(val):
            return str(val).strip() if val and str(val).strip().lower() not in ["none", "null", "unknown", "unavailable"] else ""

        # Merge Priorities
        # Road Name: Nominatim -> Photon -> Overpass -> Cache
        m_road = safe_val(nom_road_raw) or safe_val(pho_road_raw) or safe_val(ovp_road_raw) or safe_val(cache_road)
        # Road Class: Overpass -> Nominatim -> Cache
        m_class = safe_val(ovp_class_raw) or safe_val(nom_class_raw) or safe_val(cache_class)
        # Landmark: Overpass -> Photon (na) -> Nominatim -> Cache
        m_lm = safe_val(ovp_lm_raw) or safe_val(nom_lm_raw) or safe_val(cache_lm)
        # Village: Photon -> Nominatim -> Overpass -> Cache
        m_village = safe_val(pho_village_raw) or safe_val(nom_village_raw) or safe_val(ovp_village_raw) or safe_val(cache_village)
        # Town: Photon -> Nominatim -> Cache
        m_town = safe_val(pho_town_raw) or safe_val(nom_town_raw) or safe_val(cache_town)
        # District: Nominatim -> Photon -> Cache
        m_district = safe_val(nom_district_raw) or safe_val(pho_district_raw) or safe_val(cache_district)
        # State: Photon -> Nominatim -> Cache
        m_state = safe_val(pho_state_raw) or safe_val(nom_state_raw) or safe_val(cache_state)
        # Country: Photon -> Nominatim -> Cache
        m_country = safe_val(pho_country_raw) or safe_val(nom_country_raw) or safe_val(cache_country)

        # UI Safety Sanitization
        final_road = self._safe_str(m_road, "Unnamed Road")
        final_class = self._safe_str(m_class, "Unknown Road Class")
        final_lm = self._safe_str(m_lm, "No Nearby Landmark")
        final_village = self._safe_str(m_village, "Village Not Available")
        final_town = self._safe_str(m_town, "Town Not Available")
        final_district = self._safe_str(m_district, "District Not Available")
        final_state = self._safe_str(m_state, "State Not Available")
        final_country = self._safe_str(m_country, "Country Not Available")
        
        road_imp = self._calculate_road_importance(final_class)
        traffic_imp = self._calculate_traffic_importance(final_class)
        
        loc = Location(
            latitude=latitude,
            longitude=longitude,
            road_name=final_road,
            street=final_road, # Derived from road
            village=final_village,
            hamlet="",
            neighbourhood="",
            suburb="",
            town=final_town,
            city=final_town, # Derived from town
            district=final_district,
            state=final_state,
            country=final_country,
            postal_code=nom_addr.get('postcode') or pho_data.get('postcode') or "",
            formatted_address="",
            google_maps_url=Config.GOOGLE_MAPS_URL.format(lat=latitude, lon=longitude),
            road_class=final_class,
            nearby_place="",
            provider="MULTI_OSM",
            provider_version="4.0",
            cached_at=datetime.datetime.now().isoformat(),
            last_verified=datetime.datetime.now().isoformat(),
            lookup_time_ms=int((time.time() - start_time) * 1000),
            cache_hit=False,
            status="SUCCESS", 
            road_importance=road_imp,
            traffic_importance=traffic_imp,
            landmark=final_lm
        )
        
        loc.formatted_address = self._build_formatted_address(loc)
        
        # Exactly formatted logs
        logger.info(
            f"\n========================\n"
            f"Coordinates\n"
            f"{latitude}\n"
            f"{longitude}\n"
            f"------------------------\n"
            f"Nominatim\n"
            f"Road\n{nom_road_raw or '-'}\n"
            f"Village\n{nom_village_raw or '-'}\n"
            f"Town\n{nom_town_raw or '-'}\n"
            f"------------------------\n"
            f"Photon\n"
            f"Road\n{pho_road_raw or '-'}\n"
            f"Village\n{pho_village_raw or '-'}\n"
            f"Town\n{pho_town_raw or '-'}\n"
            f"------------------------\n"
            f"Overpass\n"
            f"Nearest Highway\n{ovp_road_raw or '-'}\n"
            f"Distance\n{ovp_data.get('road_dist', '-')}m\n"
            f"Landmark\n{ovp_lm_raw or '-'}\n"
            f"Distance\n{ovp_data.get('landmark_dist', '-')}m\n"
            f"------------------------\n"
            f"Merged Result\n"
            f"Road\n{loc.road_name}\n"
            f"Road Class\n{loc.road_class}\n"
            f"Landmark\n{loc.landmark}\n"
            f"Village\n{loc.village}\n"
            f"Town\n{loc.town}\n"
            f"District\n{loc.district}\n"
            f"State\n{loc.state}\n"
            f"Country\n{loc.country}\n"
            f"Formatted Address\n{loc.formatted_address}\n"
            f"\nCache Status\nMISS\n"
            f"\nLookup Time\n{loc.lookup_time_ms} ms\n"
            f"========================"
        )
        
        return loc

    def _geocode_worker(self, latitude: float, longitude: float):
        logger.info(f"[GEOCODER] [THREAD] Background refresh started for {latitude}, {longitude}")
        
        cached_loc = self.cache_service.get_closest_location(latitude, longitude)
        
        def attempt_fetch():
            return self._fetch_location(latitude, longitude, existing_cache=cached_loc)
            
        location = GeocoderRetryEngine.execute_with_retry(
            attempt_fetch, 
            max_retries=Config.GEOCODER_MAX_RETRIES, 
            retry_delay=Config.GEOCODER_RETRY_DELAY
        )
        
        if location:
            self.cache_service.save_location(location)
            logger.info(f"[GEOCODER] [SUCCESS] Background geocoded {latitude}, {longitude}")

    def geocode_async(self, latitude: float, longitude: float):
        self.executor.submit(self._geocode_worker, latitude, longitude)

geocoder_service = ReverseGeocoderService()
