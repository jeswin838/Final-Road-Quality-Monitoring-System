import logging
from models.hazard import Hazard
from services.risk_engine import RiskEngine
from services.priority_engine import PriorityEngine

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')

def test_priority_engine():
    print("--- TESTING PRIORITY ENGINE ---")
    
    # 1. Critical Hazard (Old, Many reports, High severity, Motorway)
    h1 = Hazard(
        hazard_id="TEST-1", latitude=10.0, longitude=10.0,
        severity="critical", confidence=0.98, report_count=12,
        created_at="2024-01-01T10:00:00Z"
    )
    h1.road_class = "Motorway"
    h1.road_importance = 100
    
    # 2. Medium Hazard (Recent, Few reports, Medium severity, Residential)
    h2 = Hazard(
        hazard_id="TEST-2", latitude=10.0, longitude=10.0,
        severity="medium", confidence=0.75, report_count=2,
        created_at="2026-07-01T10:00:00Z"
    )
    h2.road_class = "Residential"
    h2.road_importance = 20
    
    # 3. New Hazard on National Highway (High Road Importance, Low Age/Reports)
    h3 = Hazard(
        hazard_id="TEST-3", latitude=10.0, longitude=10.0,
        severity="high", confidence=0.88, report_count=1,
        created_at="2026-07-16T10:00:00Z"
    )
    h3.road_class = "National Highway"
    h3.road_importance = 90
    
    hazards = [h1, h2, h3]
    
    # 1. Run Risk Engine
    RiskEngine.calculate_all(hazards)
    
    # 2. Run Priority Engine
    hazards = PriorityEngine.calculate_all(hazards)
    
    print("\n--- RESULTS ---")
    for h in hazards:
        print(f"\n[Hazard {h.hazard_id}] Rank: {h.priority_rank} (Queue Pos: {h.repair_queue_position})")
        print(f"Risk Score: {h.risk_score} | Priority Score: {h.priority_score} ({h.priority})")
        print(f"Road Class: {h.road_class} | Traffic Score: {h.traffic_score}")
        print(f"Repair Category: {h.repair_category} | Window: {h.maintenance_window}")
        print(f"Contract Team Required: {h.requires_contract_team} | Senior Eng: {h.requires_senior_engineer}")
        print(f"Recommendation: {h.priority_reason}")

if __name__ == "__main__":
    test_priority_engine()
