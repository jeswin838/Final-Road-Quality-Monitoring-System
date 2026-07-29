import logging
from models.hazard import Hazard
from services.risk_engine import RiskEngine
from services.priority_engine import PriorityEngine
from services.workforce_engine import WorkforceEngine

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')

def test_workforce():
    print("--- TESTING WORKFORCE MANAGEMENT SYSTEM ---")
    
    # 1. Critical Hazard (Motorway, Verified)
    h1 = Hazard(
        hazard_id="TEST-1", latitude=10.0, longitude=10.0,
        severity="critical", confidence=0.98, report_count=12,
        created_at="2024-01-01T10:00:00Z", maintenance_state="Verified"
    )
    h1.road_class = "Motorway"
    h1.road_importance = 100
    h1.zone = "Municipal"
    
    # 2. Medium Hazard (Residential, Verified)
    h2 = Hazard(
        hazard_id="TEST-2", latitude=10.0, longitude=10.0,
        severity="medium", confidence=0.75, report_count=2,
        created_at="2026-07-01T10:00:00Z", maintenance_state="Verified"
    )
    h2.road_class = "Residential"
    h2.road_importance = 20
    h2.zone = "Municipal"
    
    # 3. New Hazard (Unverified, low confidence) - Should NOT be assigned
    h3 = Hazard(
        hazard_id="TEST-3", latitude=10.0, longitude=10.0,
        severity="low", confidence=0.40, report_count=1,
        created_at="2026-07-16T10:00:00Z", maintenance_state="Detected"
    )
    h3.road_class = "Village Road"
    h3.road_importance = 40
    h3.zone = "Municipal"
    
    hazards = [h1, h2, h3]
    
    RiskEngine.calculate_all(hazards)
    hazards = PriorityEngine.calculate_all(hazards)
    
    wf_engine = WorkforceEngine.get_instance()
    hazards = wf_engine.process(hazards)
    
    print("\n--- RESULTS ---")
    for h in hazards:
        print(f"\n[Hazard {h.hazard_id}] State: {h.maintenance_state}")
        if h.assigned_worker_id:
            print(f"Assigned To: {h.assigned_worker_name} ({h.assigned_team})")
            print(f"Assignment ID: {h.assignment_id}")
            print("History:")
            for event in h.history:
                print(f"  - {event['state']} at {event['timestamp']} (Reason: {event.get('reason', '')})")
        else:
            print("Not Assigned.")

if __name__ == "__main__":
    test_workforce()
