import time
import math
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, List, Dict, Any

from config import Config
from models.hazard import Hazard
from utils.helpers import haversine, resolve_severity

# Configure logger
logger = logging.getLogger("HazardRegistry")
logger.setLevel(logging.INFO)
if not logger.handlers:
    ch = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    
# Background Task Executor for performance requirement 14
# Handles async single-hazard recalculations
background_executor = ThreadPoolExecutor(max_workers=4)

class HazardRegistryCache:
    """Manages the in-memory cache representation of normalized municipal hazards."""
    def __init__(self):
        self.data: Dict[str, Hazard] = {}
        self.sorted_keys: List[str] = [] # Maintain sorted order by priority_score
        self.initialized: bool = False
        self._global_json_cache = None
        self.lock = threading.Lock()
        
    def invalidate(self, rebuild: bool = False):
        """Clear the cache entirely or mark as stale and trigger a background rebuild."""
        with self.lock:
            self.data.clear()
            self.sorted_keys.clear()
            self.initialized = False
            self._global_json_cache = None
            logger.info("Hazard registry cache explicitly invalidated.")
            if rebuild:
                logger.info("[HazardRegistryCache] Triggering rebuild")
                
        if rebuild:
            from services.hazard_registry import load_all_hazards, background_executor
            background_executor.submit(load_all_hazards)
        
    def is_stale(self) -> bool:
        """Check if the cache has never been initialized."""
        return not self.initialized
        
    def _find_insert_index(self, score: float) -> int:
        """Find the index to insert maintaining descending order of priority_score."""
        low, high = 0, len(self.sorted_keys)
        while low < high:
            mid = (low + high) // 2
            mid_hazard = self.data[self.sorted_keys[mid]]
            mid_score = getattr(mid_hazard, 'priority_score', 0)
            if score > mid_score:
                high = mid
            else:
                low = mid + 1
        return low
        
    def _precompute_dict(self, hazard: Hazard):
        """Precompute JSON serialization for O(1) response caching."""
        d = hazard.to_dict()
        if hasattr(hazard, 'assignment') and hazard.assignment:
            d["assignment"] = hazard.assignment
            if d["assignment"].get("status"):
                d["status"] = d["assignment"]["status"]
        else:
            d["assignment"] = None
        hazard._cached_dict = d

    def update_hazard_in_cache(self, hazard: Hazard):
        """Update or insert a single hazard into the cache, maintaining sorted order."""
        with self.lock:
            score = getattr(hazard, 'priority_score', 0)
            if hazard.hazard_id in self.data:
                try:
                    self.sorted_keys.remove(hazard.hazard_id)
                except ValueError:
                    pass
            
            self._precompute_dict(hazard)
            self.data[hazard.hazard_id] = hazard
            
            # O(1) insert maintaining sorted order
            idx = self._find_insert_index(score)
            self.sorted_keys.insert(idx, hazard.hazard_id)
            self.initialized = True
            self._global_json_cache = None
            
    def remove_hazard(self, hazard_id: str):
        """Remove a hazard from the cache."""
        with self.lock:
            if hazard_id in self.data:
                del self.data[hazard_id]
            try:
                self.sorted_keys.remove(hazard_id)
                self._global_json_cache = None
            except ValueError:
                pass
                
    def get_all(self) -> List[Hazard]:
        with self.lock:
            # Yield pre-sorted objects
            return [self.data[k] for k in self.sorted_keys if k in self.data]
            
    def get(self, master_id: str):
        """Fetch a single hazard directly from the cache."""
        with self.lock:
            return self.data.get(master_id)
            
    def get_all_json(self) -> List[Dict]:
        """Return O(1) precomputed JSON response for all hazards."""
        with self.lock:
            if self._global_json_cache is not None:
                return self._global_json_cache
                
            cached_list = []
            for k in self.sorted_keys:
                h = self.data.get(k)
                if h:
                    if not hasattr(h, '_cached_dict'):
                        self._precompute_dict(h)
                    cached_list.append(h._cached_dict)
                    
            self._global_json_cache = cached_list
            return self._global_json_cache
            
    def set_all(self, hazards: List[Hazard]):
        """Bulk initialize the cache (rebuild)."""
        with self.lock:
            self.data.clear()
            self.sorted_keys.clear()
            
            # Sort once (O(N log N)) instead of every request
            hazards.sort(key=lambda h: getattr(h, 'priority_score', 0), reverse=True)
            
            cached_list = []
            for h in hazards:
                self._precompute_dict(h)
                self.data[h.hazard_id] = h
                self.sorted_keys.append(h.hazard_id)
                cached_list.append(h._cached_dict)
                
            self._global_json_cache = cached_list
            self.initialized = True


        
    def is_stale(self) -> bool:
        with self.lock:
            return not self.initialized

# Global cache instance
registry_cache = HazardRegistryCache()

def load_assignments() -> Dict[int, Dict[str, Any]]:
    """
    Fetch the LATEST assignment for every hazard from Supabase.
    Returns a dict keyed by both hazard_id (int) and prefixed IDs like 'AI-123'.
    
    IMPORTANT: This reads directly from Supabase so it always returns live data.
    SQLite is no longer used for assignment lookups.
    """
    try:
        from app import supabase
        if not supabase:
            logger.warning("[CACHE] Supabase client unavailable for load_assignments.")
            return {}

        # Fetch the most recent assignment row per hazard (by descending id)
        res = supabase.table("assignments").select(
            "id, hazard_id, hazard_source, worker_id, worker_name, worker_email, "
            "status, verification_status, assigned_by, assigned_by_name, "
            "accepted_at, travelling_at, reached_at, repair_started_at, "
            "repair_completed_at, verified_at, completed_at, admin_notes, "
            "current_lat, current_lon, before_photo, after_photo, "
            "before_photo_lat, before_photo_lon, after_photo_lat, after_photo_lon, "
            "priority, risk_score"
        ).order("id", desc=True).execute()

        assigns: Dict[Any, Dict] = {}
        seen_hazard_ids = set()

        for a in (res.data or []):
            hid = a.get("hazard_id")
            if hid is None or hid in seen_hazard_ids:
                # Only keep the most recent row per hazard
                continue
            seen_hazard_ids.add(hid)

            # Skip terminal/archive statuses so they don't pollute active monitoring
            # (Completed/Rejected rows are preserved in DB but not in active cache)
            status = a.get("status", "")

            # Index by both integer id and prefixed string id
            assigns[hid] = a
            h_source = a.get("hazard_source", "")
            if h_source == "USER":
                assigns[f"USER-{hid}"] = a
            else:
                assigns[f"AI-{hid}"] = a

        logger.info(f"[CACHE] load_assignments loaded {len(seen_hazard_ids)} assignments from Supabase.")
        return assigns

    except Exception as e:
        logger.exception(f"[CACHE] load_assignments failed: {e}")
        return {}

def normalize_record(record: Dict[str, Any], source_type: str, assigns: Dict[int, Dict[str, Any]]) -> Hazard:
    """Safely map database column variants into standard Hazard objects."""
    lat = float(record.get("latitude") or record.get("gps_lat") or 0.0)
    lon = float(record.get("longitude") or record.get("gps_lon") or 0.0)
    
    rec_id = record.get("id")
    # Stable database identifiers
    if source_type == "AI":
        hazard_id = f"AI-{rec_id}"
    else:
        hazard_id = f"USER-{rec_id}"
        
    # Standardize image path urls
    url = record.get("image_url") or record.get("media_url") or record.get("image")
    if url and not url.startswith("http") and not url.startswith("/static"):
        url = f"{Config.SUPABASE_URL}/storage/v1/object/public/pothole-images/{url}"
        
    severity = str(record.get("severity") or "Unknown").lower()
    confidence = float(record.get("confidence") or 0.0)
    status = str(record.get("status") or "Detected")
    
    assigned_worker = None
    maintenance_status = None
    assignment_dict = {}
    
    if hazard_id in assigns:
        assigned_worker = assigns[hazard_id].get("worker_name") or assigns[hazard_id].get("worker_id")
        maintenance_status = assigns[hazard_id].get("status")
        status = assigns[hazard_id].get("status") or status
        assignment_dict = assigns[hazard_id]
        
    elif rec_id in assigns: # Legacy fallback
        assigned_worker = assigns[rec_id].get("worker_name") or assigns[rec_id].get("worker_id")
        maintenance_status = assigns[rec_id].get("status")
        status = assigns[rec_id].get("status") or status
        assignment_dict = assigns[rec_id]
        
    return Hazard(
        hazard_id=hazard_id,
        db_id=int(rec_id) if rec_id else 0,
        latitude=lat,
        longitude=lon,
        severity=severity,
        confidence=confidence,
        status=status,
        source=source_type,
        image_url=url,
        created_at=record.get("created_at"),
        updated_at=record.get("updated_at") or record.get("created_at"),
        report_count=int(record.get("report_count") or 1),
        worker=assigned_worker,
        maintenance_state=maintenance_status,
        assignment=assignment_dict
    )

def build_or_merge_hazard(new_h: Hazard, master_hazard: Optional[Hazard] = None) -> Hazard:
    """
    ONE reusable hazard creation/merge pipeline.
    Handles duplicate detection, clustering, report_count, highest confidence, 
    image list, history, original_reports, and severity resolution.
    """
    if master_hazard is not None:
        # Merge into existing
        master_hazard.report_count += getattr(new_h, 'report_count', 1)
        
        if new_h.confidence > master_hazard.highest_confidence:
            master_hazard.highest_confidence = new_h.confidence
            
        h_time = new_h.created_at or ""
        gh_time = master_hazard.latest_report_time or ""
        if h_time > gh_time:
            master_hazard.latest_report_time = h_time
            
        if new_h.image_url and new_h.image_url not in master_hazard.images:
            master_hazard.images.append(new_h.image_url)
            
        master_hazard.original_reports.append(new_h)
        
        hist_type = "Detection" if new_h.source == "AI" else "Citizen Report"
        master_hazard.history.append({
            "history_type": hist_type,
            "timestamp": new_h.created_at,
            "status": new_h.status,
            "worker": new_h.worker,
            "worker_team": getattr(new_h, "worker_team", None),
            "note": getattr(new_h, "reason", None) or getattr(new_h, "description", None),
            "source": new_h.source,
            "confidence": new_h.confidence,
            "severity": new_h.severity,
            "image": new_h.image_url
        })
        
        sevs = [orig.severity for orig in master_hazard.original_reports]
        master_hazard.severity = resolve_severity(sevs)
        
        # PRESERVE ACTIVE ASSIGNMENT
        terminal_statuses = ["Completed", "Closed", "Rejected", "Cancelled"]
        
        master_has_active = (
            master_hazard.assignment and 
            master_hazard.assignment.get("status") and 
            master_hazard.assignment.get("status") not in terminal_statuses
        )
        
        new_h_has_active = (
            new_h.assignment and 
            new_h.assignment.get("status") and 
            new_h.assignment.get("status") not in terminal_statuses
        )
        
        if new_h_has_active and not master_has_active:
            master_hazard.assignment = new_h.assignment
            master_hazard.worker = new_h.worker
            master_hazard.maintenance_state = new_h.maintenance_state
            master_hazard.status = new_h.status
            # Preserve the hazard_id of the one that holds the active assignment
            # so DB updates apply to the correct assignment record.
            master_hazard.hazard_id = new_h.hazard_id
            
        return master_hazard
    else:
        # Initialize as brand new master
        new_h.report_count = getattr(new_h, 'report_count', 1) or 1
        new_h.latest_report_time = new_h.created_at
        new_h.highest_confidence = new_h.confidence
        new_h.images = [new_h.image_url] if new_h.image_url else []
        new_h.original_reports = [new_h]
        
        hist_type = "Detection" if new_h.source == "AI" else "Citizen Report"
        new_h.history = [{
            "history_type": hist_type,
            "timestamp": new_h.created_at,
            "status": new_h.status,
            "worker": new_h.worker,
            "worker_team": getattr(new_h, "worker_team", None),
            "note": getattr(new_h, "reason", None) or getattr(new_h, "description", None),
            "source": new_h.source,
            "confidence": new_h.confidence,
            "severity": new_h.severity,
            "image": new_h.image_url
        }]
        
        new_h.severity = resolve_severity([new_h.severity])
        return new_h

def merge_sources(ai_potholes: List[Hazard], citizen_reports: List[Hazard]) -> List[Hazard]:
    """Cluster co-located hazards spatially (50m radius) into master municipal hazards."""
    start_time = time.time()
    all_hazards = ai_potholes + citizen_reports
    # Sort descending by created_at so newest record serves as master anchor
    all_hazards.sort(key=lambda h: h.created_at or "", reverse=True)
    
    grid = {}
    CELL_SIZE = 0.0005  # ~55m grid mapping
    grouped_hazards: List[Hazard] = []
    
    def get_cell_keys(lat, lon):
        x, y = math.floor(lat / CELL_SIZE), math.floor(lon / CELL_SIZE)
        return [(x+dx, y+dy) for dx in (-1,0,1) for dy in (-1,0,1)]
        
    for h in all_hazards:
        found = False
        keys = get_cell_keys(h.latitude, h.longitude)
        for k in keys:
            if k in grid:
                for gh in grid[k]:
                    if haversine(h.latitude, h.longitude, gh.latitude, gh.longitude) < 50.0:
                        build_or_merge_hazard(h, master_hazard=gh)
                        found = True
                        break
            if found:
                break
                
        if not found:
            build_or_merge_hazard(h, master_hazard=None)
            grouped_hazards.append(h)
            x, y = math.floor(h.latitude / CELL_SIZE), math.floor(h.longitude / CELL_SIZE)
            grid.setdefault((x, y), []).append(h)
        
    merge_time = time.time() - start_time
    logger.info(f"Deduplication complete: merged {len(all_hazards)} records into {len(grouped_hazards)} unique municipal hazards (Merge Time: {merge_time:.4f}s)")
    return grouped_hazards

def load_all_hazards() -> List[Hazard]:
    """Fetch, normalize, and group raw hazards. Serving cache if initialized."""
    start_time = time.time()
    
    if not registry_cache.is_stale():
        return registry_cache.get_all()
        
    logger.info("Cache status: MISS. Fetching raw database layers...")
    
    # Fetch from repository layer
    repo_start = time.time()
    from repositories import hazard_repository
    
    ai_potholes_raw = hazard_repository.fetch_raw_ai_potholes()
    user_reports_raw = hazard_repository.fetch_raw_citizen_reports()
    assigns = load_assignments()
    
    repo_time = time.time() - repo_start
    
    # Normalize records
    norm_start = time.time()
    ai_potholes = []
    for r in ai_potholes_raw:
        try:
            ai_potholes.append(normalize_record(r, "AI", assigns))
        except Exception as ex:
            logger.error(f"Error normalizing AI record {r.get('id')}: {ex}")
            
    citizen_reports = []
    for r in user_reports_raw:
        try:
            citizen_reports.append(normalize_record(r, "Citizen", assigns))
        except Exception as ex:
            logger.error(f"Error normalizing user report {r.get('id')}: {ex}")
            
    norm_time = time.time() - norm_start
    
    # Group and merge
    merged_hazards = merge_sources(ai_potholes, citizen_reports)
    
    # Phase 2: Reverse Geocode Enrichment (Synchronous)
    from services.reverse_geocoder import geocoder_service
    from models.location import Location
    import datetime
    
    session_geo_cache = {}
    unique_coords = set()
    geo_cache_hits = 0
    geo_cache_misses = 0
    geo_api_calls = 0
    
    for h in merged_hazards:
        lat_round = round(float(h.latitude), 6)
        lon_round = round(float(h.longitude), 6)
        coord_key = (lat_round, lon_round)
        unique_coords.add(coord_key)
        
        # 1. Check fast session cache first (in-memory during this registry build)
        cached_loc = session_geo_cache.get(coord_key)
        
        if cached_loc:
            geo_cache_hits += 1
            cached_loc.cache_hit = True
        else:
            # 2. Check the LocationCacheService (O(1) dictionary now)
            cached_loc = geocoder_service.cache_service.get_closest_location(lat_round, lon_round)
            
            if not cached_loc or getattr(cached_loc, 'status', '') != "SUCCESS":
                geo_cache_misses += 1
                geo_api_calls += 1
                
                # 3. Only fetch from APIs if it truly doesn't exist or isn't successful
                loc = geocoder_service._fetch_location(lat_round, lon_round, existing_cache=cached_loc)
                if loc:
                    geocoder_service.cache_service.save_location(loc)
                    cached_loc = loc
                else:
                    # Absolute worst-case fallback, save failure to avoid repeating on next boot
                    cached_loc = Location(
                        latitude=lat_round, 
                        longitude=lon_round, 
                        status="FAILED",
                        cached_at=datetime.datetime.now().isoformat()
                    )
                    geocoder_service.cache_service.save_location(cached_loc)
            else:
                geo_cache_hits += 1
                
            # Populate session cache for subsequent hazards sharing these coords
            session_geo_cache[coord_key] = cached_loc
            
        if cached_loc:
            h.reverse_geocoded = True
            h.formatted_address = getattr(cached_loc, 'formatted_address', 'Location unavailable')
            h.google_maps_url = getattr(cached_loc, 'google_maps_url', '')
            h.road_name = getattr(cached_loc, 'road_name', 'Unknown Road')
            h.street = getattr(cached_loc, 'street', '')
            h.village = getattr(cached_loc, 'village', '')
            h.hamlet = getattr(cached_loc, 'hamlet', '')
            h.neighbourhood = getattr(cached_loc, 'neighbourhood', '')
            h.suburb = getattr(cached_loc, 'suburb', '')
            h.town = getattr(cached_loc, 'town', '')
            h.district = getattr(cached_loc, 'district', 'Unknown')
            h.state = getattr(cached_loc, 'state', '')
            h.country = getattr(cached_loc, 'country', '')
            h.postal_code = getattr(cached_loc, 'postal_code', '')
            h.road_class = getattr(cached_loc, 'road_class', 'Unknown')
            h.nearby_place = getattr(cached_loc, 'nearby_place', '')
            h.landmark = getattr(cached_loc, 'landmark', 'Unavailable')
            h.road_importance = getattr(cached_loc, 'road_importance', 10)
            h.traffic_importance = getattr(cached_loc, 'traffic_importance', 'Unknown')
            
            if hasattr(cached_loc, 'city'):
                if not h.town: h.town = cached_loc.city
        else:
            h.reverse_geocoded = False
            h.road_class = "Unknown"
            h.road_importance = 10
            h.traffic_importance = "Unknown"
            h.landmark = "Unavailable"
            
        cache_status = "Cache Hit" if getattr(cached_loc, 'cache_hit', False) else "Cache Miss"
        
        # Structured Logging for Data Tracing (Phase 10B)
        logger.info(
            f"[{h.latitude}, {h.longitude}] -> "
            f"{h.road_name} -> "
            f"{h.landmark} -> "
            f"{h.village} -> "
            f"{h.district} -> "
            f"{h.road_class} -> "
            f"{h.road_importance} -> "
            f"{h.traffic_importance} -> "
            f"{cache_status} -> "
            f"Returned to Hazard Registry"
        )

    # Phase 3: Risk Intelligence Engine (O(N) non-blocking)
    try:
        from services.risk_engine import RiskEngine
        RiskEngine.calculate_all(merged_hazards)
    except Exception as e:
        logger.exception(f"RiskEngine failed: {e}")
    
    # Phase 4: Priority Engine (O(N log N) sorting non-blocking)
    try:
        from services.priority_engine import PriorityEngine
        PriorityEngine.calculate_all(merged_hazards)
    except Exception as e:
        logger.exception(f"PriorityEngine failed: {e}")
    
    # Phase 5a: Reasoning Engine
    try:
        from services.reasoning_engine import ReasoningEngine
        ReasoningEngine.process_all(merged_hazards)
    except Exception as e:
        logger.exception(f"ReasoningEngine failed: {e}")
    
    # Phase 5b: Workforce Management System (Assignment Engine)
    try:
        from services.workforce_engine import WorkforceEngine
        wf_engine = WorkforceEngine.get_instance()
        wf_engine.process(merged_hazards)
    except Exception as e:
        logger.exception(f"WorkforceEngine failed: {e}")
            
    registry_cache.set_all(merged_hazards)
    
    total_time = time.time() - start_time
    
    # Task 7: Advanced Performance Logging
    logger.info(
        f"\n=====================================\n"
        f"[REGISTRY REBUILD COMPLETE]\n"
        f"Unique Coordinates: {len(unique_coords)}\n"
        f"Geocoder Cache Hits: {geo_cache_hits}\n"
        f"Geocoder Cache Misses: {geo_cache_misses}\n"
        f"Geocoder API Calls: {geo_api_calls}\n"
        f"Repository Time: {repo_time:.4f}s\n"
        f"Normalization Time: {norm_time:.4f}s\n"
        f"Total Initialization Time: {total_time:.4f}s\n"
        f"====================================="
    )
    
    return registry_cache.get_all()

def load_hazard(hazard_id: str) -> Optional[Hazard]:
    """Retrieve a single grouped Hazard object by ID."""
    hazards = load_all_hazards()
    for h in hazards:
        if h.hazard_id == hazard_id:
            return h
    return None

def find_nearby(lat: float, lon: float, radius_m: float = 50.0) -> List[Hazard]:
    """Retrieve all hazards within radius_m of target coords directly from in-memory cache."""
    nearby = []
    with registry_cache.lock:
        for h in registry_cache.data.values():
            if haversine(lat, lon, h.latitude, h.longitude) <= radius_m:
                nearby.append(h)
    return nearby

def count_reports() -> Dict[str, int]:
    """Return hazard count statistics."""
    hazards = load_all_hazards()
    total_raw = sum(h.report_count for h in hazards)
    return {
        "unique_hazards": len(hazards),
        "total_reports": total_raw
    }

def get_latest(limit: int = 10) -> List[Hazard]:
    """Retrieve the newest grouped hazards."""
    hazards = load_all_hazards()
    hazards.sort(key=lambda h: h.created_at or "", reverse=True)
    return hazards[:limit]
    
def patch_hazard_assignment(master_id: str, assignment_data: Dict[str, Any]):
    """
    Surgically update ONLY the assignment fields of a single hazard in the cache.
    This is the fastest possible cache update — no DB fetch, no engine recalculation.
    
    Use this immediately after any Supabase assignment write for instant UI sync.
    Falls back to full recalculate_single_hazard if the hazard is not found in cache.
    
    Args:
        master_id: The prefixed hazard ID, e.g. 'AI-123' or 'USER-456'
        assignment_data: The latest assignment dict from Supabase
    """
    with registry_cache.lock:
        target_hazard = registry_cache.data.get(master_id)

    if not target_hazard:
        logger.warning(f"[CACHE] patch_hazard_assignment: {master_id} not in cache — triggering full recalculate.")
        recalculate_single_hazard(master_id, None, None, "assignment_update")
        return

    target_hazard.assignment = assignment_data
    target_hazard.worker = assignment_data.get("worker_name") or assignment_data.get("worker_id") or ""
    target_hazard.assigned_worker_name = assignment_data.get("worker_name") or ""
    target_hazard.assigned_worker_id = assignment_data.get("worker_id") or ""
    target_hazard.assignment_status = assignment_data.get("status") or "Unassigned"
    target_hazard.assignment_time = assignment_data.get("assigned_time") or assignment_data.get("created_at") or ""
    
    target_hazard.accepted_at = assignment_data.get("accepted_at") or target_hazard.accepted_at
    target_hazard.started_at = assignment_data.get("repair_started_at") or assignment_data.get("started_at") or target_hazard.started_at
    target_hazard.completed_at = assignment_data.get("repair_completed_at") or assignment_data.get("completed_at") or target_hazard.completed_at
    target_hazard.verified_at = assignment_data.get("verified_at") or target_hazard.verified_at
    
    # Store other specific lifecycle fields in the assignment dict so to_dict can access them
    # Ensure they are present if provided by Supabase
    if "travelling_at" in assignment_data:
        target_hazard.assignment["travelling_at"] = assignment_data["travelling_at"]
    if "reached_at" in assignment_data:
        target_hazard.assignment["reached_at"] = assignment_data["reached_at"]

    new_status = assignment_data.get("status")
    if new_status:
        target_hazard.maintenance_state = new_status
        target_hazard.status = new_status

    import datetime
    target_hazard.updated_at = datetime.datetime.utcnow().isoformat()
    
    # Generate the cached JSON directly on the hazard object
    target_hazard._cached_dict = target_hazard.to_dict()

    # Invalidate the precomputed JSON dict for this hazard and the global list cache
    registry_cache._precompute_dict(target_hazard)
    registry_cache.data[master_id] = target_hazard
    registry_cache._global_json_cache = None  # Force /api/alerts to re-serialize

    logger.info(
        f"[CACHE] [REGISTRY UPDATED] {master_id} | "
        f"status={new_status} | worker={target_hazard.worker} | "
        f"[ALERT CACHE REFRESHED]"
    )

def refresh_assignment_cache(master_id, hazard_id):
    try:
        from app import supabase
    except ImportError:
        supabase = None
    if not supabase:
        from routes.api import get_supabase
        supabase = get_supabase()

    latest = (
        supabase.table("assignments")
        .select("*")
        .eq("hazard_id", hazard_id)
        .order("id", desc=True)
        .limit(1)
        .execute()
    )

    if latest.data:
        latest_row = latest.data[0]
        patch_hazard_assignment(master_id, latest_row)
        print("[WORKFLOW] Cache refreshed")
        print(f"Hazard ID: {hazard_id}")
        print(f"Assignment ID: {latest_row.get('id')}")
        print(f"Latest Status: {latest_row.get('status')}")

def recalculate_single_hazard_async(hazard_id: str, new_db_record: Optional[Dict[str, Any]] = None, source: Optional[str] = None, event_type: str = "update"):
    """
    Submits a recalculation job to the background thread pool, allowing APIs to return instantly.
    """
    background_executor.submit(recalculate_single_hazard, hazard_id, new_db_record, source, event_type)

def recalculate_single_hazard(hazard_id: str, new_db_record: Optional[Dict[str, Any]] = None, source: Optional[str] = None, event_type: str = "update") -> Optional[Hazard]:
    """
    Granular recalculation of a single hazard. Updates cache without rebuilding the world.
    Supports events like 'new_detection', 'status_update', 'assignment_update'.
    """
    from services.risk_engine import RiskEngine
    from services.priority_engine import PriorityEngine
    from services.reasoning_engine import ReasoningEngine
    from services.workforce_engine import WorkforceEngine
    from services.reverse_geocoder import geocoder_service
    import datetime

    target_hazard = registry_cache.data.get(hazard_id)
    
    # Check if it was clustered into another hazard
    if not target_hazard:
        for master in registry_cache.data.values():
            if any(orig.hazard_id == hazard_id for orig in master.original_reports):
                target_hazard = master
                break

    # For status updates, reload the latest DB record to ensure we preserve all fields
    if event_type == "status_update":
        try:
            from app import supabase
            db_id_str = hazard_id.replace("AI-", "").replace("USER-", "")
            table_name = "potholes" if "AI-" in hazard_id else "user_reports"
            res = supabase.table(table_name).select("*").eq("id", db_id_str).execute()
            
            if res.data:
                latest_db_record = res.data[0]
                source_type = "AI" if "AI-" in hazard_id else "Citizen"
                assigns = load_assignments()
                updated_h = normalize_record(latest_db_record, source_type, assigns)
                
                if target_hazard:
                    terminal_statuses = ["Completed", "Closed", "Rejected", "Cancelled"]
                    has_active_assignment = (
                        target_hazard.assignment and 
                        target_hazard.assignment.get("status") and 
                        target_hazard.assignment.get("status") not in terminal_statuses
                    )

                    if not has_active_assignment:
                        target_hazard.status = updated_h.status
                        target_hazard.worker = updated_h.worker
                        target_hazard.maintenance_state = updated_h.maintenance_state
                        target_hazard.assignment = updated_h.assignment

                    target_hazard.severity = updated_h.severity
                    target_hazard.confidence = updated_h.confidence
                    target_hazard.updated_at = updated_h.updated_at
                    
                    for orig in target_hazard.original_reports:
                        if orig.hazard_id == hazard_id:
                            orig.status = updated_h.status
                            orig.severity = updated_h.severity
                            orig.confidence = updated_h.confidence
                            if not has_active_assignment:
                                orig.worker = updated_h.worker
                                orig.maintenance_state = updated_h.maintenance_state
                                orig.assignment = updated_h.assignment
                            orig.updated_at = updated_h.updated_at
                            break
                else:
                    # Target hazard wasn't in cache (e.g. newly approved citizen report).
                    # Treat it as a new detection to cluster and add it.
                    event_type = "new_detection"
                    new_db_record = latest_db_record
                    source = source_type
            else:
                logger.warning(f"recalculate_single_hazard: DB record not found for {hazard_id}")
        except Exception as e:
            logger.error(f"Failed to fetch updated record for {hazard_id}: {e}")
            if new_db_record and target_hazard:
                target_hazard.status = new_db_record.get("status", target_hazard.status)

    # For a brand new hazard (or a newly approved one being integrated)
    if event_type == "new_detection" and new_db_record and source:
        if not target_hazard:
            lat = float(new_db_record.get("latitude") or new_db_record.get("gps_lat") or 0.0)
            lon = float(new_db_record.get("longitude") or new_db_record.get("gps_lon") or 0.0)
            
            assigns = load_assignments()
            new_h = normalize_record(new_db_record, source, assigns)
            
            nearby = find_nearby(lat, lon, radius_m=50.0)
            before_size = len(registry_cache.data)
            
            if nearby:
                master = nearby[0]
                build_or_merge_hazard(new_h, master_hazard=master)
                target_hazard = master
                inserted = False
                logger.info(f"[RUNTIME SYNC] Merged {new_h.hazard_id} into {master.hazard_id}")
            else:
                build_or_merge_hazard(new_h, master_hazard=None)
                target_hazard = new_h
                inserted = True
                logger.info(f"[RUNTIME SYNC] Created new master hazard {new_h.hazard_id}")
            
            # Immediately refresh the JSON cache via update_hazard_in_cache
            registry_cache.update_hazard_in_cache(target_hazard)
            after_size = len(registry_cache.data)
            
            logger.info(
                f"[RUNTIME DETECTION]\n"
                f"Hazard ID: {new_h.hazard_id}\n"
                f"Latitude: {new_h.latitude}\n"
                f"Longitude: {new_h.longitude}\n"
                f"Nearby hazards found: {len(nearby)}\n"
                f"Merged? {'YES' if nearby else 'NO'}\n"
                f"Inserted? {'YES' if inserted else 'NO'}\n"
                f"Registry size before: {before_size}\n"
                f"Registry size after: {after_size}\n"
                f"JSON cache refreshed: YES"
            )

    elif event_type == "assignment_update" and target_hazard:
        assigns = load_assignments()
        if target_hazard.hazard_id in assigns:
            a_data = assigns[target_hazard.hazard_id]
            target_hazard.worker = a_data.get("worker_name") or a_data.get("worker_id")
            target_hazard.maintenance_state = a_data.get("status")
            target_hazard.status = target_hazard.maintenance_state
            target_hazard.assignment = a_data
        else:
            if target_hazard.db_id in assigns:
                a_data = assigns[target_hazard.db_id]
                target_hazard.worker = a_data.get("worker_name") or a_data.get("worker_id")
                target_hazard.maintenance_state = a_data.get("status")
                target_hazard.status = target_hazard.maintenance_state
                target_hazard.assignment = a_data
                
    if not target_hazard:
        logger.warning(f"recalculate_single_hazard: target_hazard not found or created for {hazard_id}")
        return None

    # 1. Reverse Geocoding Check (Only if missing)
    if not target_hazard.formatted_address or target_hazard.formatted_address == "Location unavailable":
        cached_loc = geocoder_service.cache_service.get_closest_location(target_hazard.latitude, target_hazard.longitude)
        if not cached_loc or cached_loc.status != "SUCCESS":
            loc = geocoder_service._fetch_location(target_hazard.latitude, target_hazard.longitude, existing_cache=cached_loc)
            if loc:
                geocoder_service.cache_service.save_location(loc)
                cached_loc = loc
                
        if cached_loc:
            target_hazard.reverse_geocoded = True
            target_hazard.formatted_address = getattr(cached_loc, 'formatted_address', 'Location unavailable')
            target_hazard.google_maps_url = getattr(cached_loc, 'google_maps_url', '')
            target_hazard.road_name = getattr(cached_loc, 'road_name', 'Unknown Road')
            target_hazard.street = getattr(cached_loc, 'street', '')
            target_hazard.village = getattr(cached_loc, 'village', '')
            target_hazard.hamlet = getattr(cached_loc, 'hamlet', '')
            target_hazard.district = getattr(cached_loc, 'district', 'Unknown')
            target_hazard.road_class = getattr(cached_loc, 'road_class', 'Unknown')
            target_hazard.road_importance = getattr(cached_loc, 'road_importance', 10)
            target_hazard.traffic_importance = getattr(cached_loc, 'traffic_importance', 'Unknown')
            if hasattr(cached_loc, 'city') and not target_hazard.town:
                target_hazard.town = cached_loc.city

    # 2. Risk Engine
    try:
        RiskEngine.calculate(target_hazard)
    except Exception as e:
        logger.exception(f"RiskEngine failed for {hazard_id}: {e}")
        
    # 3. Priority Engine
    try:
        PriorityEngine.calculate(target_hazard)
    except Exception as e:
        logger.exception(f"PriorityEngine failed for {hazard_id}: {e}")
        
    # 4. Reasoning Engine
    try:
        ReasoningEngine.process(target_hazard)
    except Exception as e:
        logger.exception(f"ReasoningEngine failed for {hazard_id}: {e}")
        
    # 5. Workforce (if required for new detections, skip on assignment_update to prevent recursion)
    if event_type == "new_detection":
        try:
            wf_engine = WorkforceEngine.get_instance()
            wf_engine.process([target_hazard])
        except Exception as e:
            logger.exception(f"WorkforceEngine failed for {hazard_id}: {e}")

    registry_cache.update_hazard_in_cache(target_hazard)
    logger.info(f"Granular recalculation complete for {target_hazard.hazard_id} ({event_type})")
    
    return target_hazard
