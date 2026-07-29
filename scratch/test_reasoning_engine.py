import logging
from models.hazard import Hazard
from services.risk_engine import RiskEngine
from services.priority_engine import PriorityEngine
from services.reasoning_engine import ReasoningEngine

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')

def test_reasoning():
    print("--- TESTING REASONING ENGINE (REASONBUNDLE) ---")
    
    # 1. Complex Hazard (School, Motorway, Critical)
    h1 = Hazard(
        hazard_id="TEST-1", latitude=10.0, longitude=10.0,
        severity="critical", confidence=0.98, report_count=22,
        created_at="2024-01-01T10:00:00Z"
    )
    h1.road_class = "Motorway"
    h1.road_importance = 100
    h1.location_summary = "Near primary school and hospital"
    
    # 2. Simple Hazard
    h2 = Hazard(
        hazard_id="TEST-2", latitude=10.0, longitude=10.0,
        severity="low", confidence=0.45, report_count=1,
        created_at="2026-07-16T10:00:00Z"
    )
    h2.road_class = "Residential"
    h2.road_importance = 10
    
    hazards = [h1, h2]
    
    RiskEngine.calculate_all(hazards)
    PriorityEngine.calculate_all(hazards)
    ReasoningEngine.process_all(hazards)
    
    print("\n--- RESULTS ---")
    for h in hazards:
        print(f"\n[Hazard {h.hazard_id}]")
        if h.reason_bundle:
            b = h.reason_bundle
            print(f"Summary         : {b.summary}")
            print(f"Rec Team        : {b.recommendations.get('team')}")
            print(f"Actions         : {', '.join(b.actions)}")
            print(f"Citizen Msg     : {b.citizen_message}")
            print(f"Engineer Msg    :\n{b.engineer_message}")
            print(f"Supervisor Msg  :\n{b.supervisor_message}")
            print(f"Processing Time : {b.processing_ms} ms")
        else:
            print("No ReasonBundle attached.")

if __name__ == "__main__":
    test_reasoning()
