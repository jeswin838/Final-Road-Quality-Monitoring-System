import time
import logging
from services.hazard_registry import load_all_hazards
from services.reverse_geocoder import geocoder_service

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')

def run_test():
    print("--- FIRST RUN ---")
    hazards = load_all_hazards()
    print(f"Loaded {len(hazards)} hazards.")
    for h in hazards[:3]:
        print(f"[{h.hazard_id}] Lat: {h.latitude}, Lon: {h.longitude}")
        print(f"  Geocoded: {h.reverse_geocoded}")
        print(f"  Address: {h.formatted_address}")
        
    print("\nWaiting 5 seconds for background geocoding to run...")
    time.sleep(5)
    
    print("\n--- REFRESH CACHE IN SERVICES ---")
    geocoder_service.cache_service.refresh_cache()
    
    print("\n--- SECOND RUN ---")
    from services.hazard_registry import registry_cache
    registry_cache.invalidate() # force refresh
    hazards2 = load_all_hazards()
    print(f"Loaded {len(hazards2)} hazards.")
    for h in hazards2[:3]:
        print(f"[{h.hazard_id}] Lat: {h.latitude}, Lon: {h.longitude}")
        print(f"  Geocoded: {h.reverse_geocoded}")
        print(f"  Address: {h.formatted_address}")
        print(f"  Road Class: {h.road_class}")
        print(f"  Maps URL: {h.google_maps_url}")

if __name__ == "__main__":
    run_test()
