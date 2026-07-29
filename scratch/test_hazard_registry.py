import os
import sys
from dotenv import load_dotenv

# Ensure workspace is in python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment
load_dotenv()

# Mock model download to avoid importing ultralytics/torch during test initialization
import sys
from unittest.mock import MagicMock
sys.modules['download_model'] = MagicMock()

def verify_hazard_registry():
    print("--- TESTING REFINED HAZARD REGISTRY SERVICE ---")
    
    try:
        from services.hazard_registry import (
            load_all_hazards,
            load_hazard,
            find_nearby,
            count_reports,
            get_latest,
            registry_cache
        )
        from models.hazard import Hazard
        from utils.helpers import resolve_severity
        
        # 0. Test resolve_severity helper
        print("\n[Test 0] Testing resolve_severity priorities...")
        assert resolve_severity(["low", "critical"]) == "critical"
        assert resolve_severity(["high", "medium", "medium"]) == "high"
        assert resolve_severity([]) == "unknown"
        print("Success: resolve_severity priorities verified.")
        
        # 1. Test load_all_hazards
        print("\n[Test 1] Loading all hazards...")
        hazards = load_all_hazards()
        print(f"Success! Loaded {len(hazards)} grouped hazards.")
        
        if not hazards:
            print("Warning: No hazards returned, but query succeeded.")
            return
            
        # Validate data types and properties of Hazard
        first = hazards[0]
        print("\nVerifying Refined Hazard Object Schema:")
        print(f" - ID: {first.hazard_id} (type: {type(first.hazard_id)})")
        print(f" - Latitude: {first.latitude} (type: {type(first.latitude)})")
        print(f" - Longitude: {first.longitude} (type: {type(first.longitude)})")
        print(f" - Severity: {first.severity} (type: {type(first.severity)})")
        print(f" - Confidence: {first.confidence} (type: {type(first.confidence)})")
        print(f" - Status: {first.status} (type: {type(first.status)})")
        print(f" - Source: {first.source} (type: {type(first.source)})")
        print(f" - Images List: {first.images} (count: {len(first.images)})")
        print(f" - History List: {len(first.history)} entries")
        print(f" - Original Reports: {len(first.original_reports)} entries")
        print(f" - Latest Report Time: {first.latest_report_time}")
        print(f" - Highest Confidence: {first.highest_confidence}")
        
        # Validate stable DB ID structure
        assert first.hazard_id.startswith("AI-") or first.hazard_id.startswith("USER-"), \
            f"ID '{first.hazard_id}' must start with 'AI-' or 'USER-'"
            
        # Validate type structure
        assert isinstance(first, Hazard), "Must be an instance of Hazard dataclass"
        assert isinstance(first.images, list), "Images must be a list"
        assert isinstance(first.history, list), "History must be a list"
        assert isinstance(first.original_reports, list), "Original reports must be a list"
        
        # Validate expanded history structure
        if first.history:
            hist_item = first.history[0]
            print("\nVerifying History Entry Schema:")
            print(f" - history_type: {hist_item.get('history_type')}")
            print(f" - timestamp: {hist_item.get('timestamp')}")
            print(f" - status: {hist_item.get('status')}")
            print(f" - worker: {hist_item.get('worker')}")
            print(f" - note: {hist_item.get('note')}")
            print(f" - image: {hist_item.get('image')}")
            assert "history_type" in hist_item
            assert "timestamp" in hist_item
            assert "status" in hist_item
            assert "worker" in hist_item
            assert "note" in hist_item
            assert "image" in hist_item

        # 2. Test load_hazard
        print("\n[Test 2] Testing load_hazard by ID...")
        single = load_hazard(first.hazard_id)
        assert single is not None, "Should fetch the hazard by ID"
        assert single.hazard_id == first.hazard_id
        print(f"Success! Loaded matching hazard: {single.hazard_id}")
        
        # 3. Test find_nearby
        print("\n[Test 3] Testing find_nearby within 100 meters...")
        nearby = find_nearby(first.latitude, first.longitude, radius_m=100.0)
        assert len(nearby) > 0, "Should find at least the anchor hazard itself"
        print(f"Success! Found {len(nearby)} hazards nearby.")
        
        # 4. Test count_reports
        print("\n[Test 4] Testing count_reports...")
        counts = count_reports()
        print(f"Success! Counts: {counts}")
        assert counts["unique_hazards"] == len(hazards)
        assert counts["total_reports"] >= len(hazards)
        
        # 5. Test Cache Operations
        print("\n[Test 5] Testing Cache Operations...")
        # Cache hit test
        print("Checking for cache hit...")
        h2 = load_all_hazards()
        assert registry_cache.is_stale() is False
        
        # Cache invalidate test
        print("Invalidating cache...")
        registry_cache.invalidate()
        assert registry_cache.is_stale() is True
        assert registry_cache.data is None
        
        # Cache refresh test
        print("Refreshing cache...")
        registry_cache.refresh()
        assert registry_cache.data is not None
        assert registry_cache.is_stale() is False
        print("Success: Cache hit, invalidate, and refresh verified.")
        
        print("\nALL REFINED HAZARD REGISTRY SERVICE UNIT TESTS PASSED SUCCESSFULLY!")
        
    except Exception as e:
        print("\nRefined Hazard Registry Service Verification Failed:")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    verify_hazard_registry()
