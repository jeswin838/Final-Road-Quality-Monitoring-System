import logging
from models.hazard import Hazard
from services.risk_engine import RiskEngine

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')

def test_risk_engine():
    print("--- TESTING RISK ENGINE ---")
    
    # 1. Critical Hazard (Old, Many reports, High severity, Motorway)
    h1 = Hazard(
        hazard_id="TEST-1", latitude=10.0, longitude=10.0,
        severity="critical", confidence=0.98, report_count=12,
        created_at="2024-01-01T10:00:00Z"
    )
    # Mock geocoded data
    h1.road_class = "Motorway"
    h1.road_importance = 100
    
    h1 = RiskEngine.calculate(h1)
    
    print("\n[Hazard 1] - Expected Critical")
    print(f"Risk Score: {h1.risk_score}, Level: {h1.risk_level}")
    print(f"Waiting Days: {h1.waiting_days}")
    print(f"Requires Supervisor: {h1.requires_supervisor}")
    print(f"Requires Emergency: {h1.requires_emergency_team}")
    print(f"Reason: {h1.risk_reason}")
    print(f"Action: {h1.recommended_action}")

    # 2. Medium Hazard (Recent, Few reports, Medium severity, Residential)
    h2 = Hazard(
        hazard_id="TEST-2", latitude=10.0, longitude=10.0,
        severity="medium", confidence=0.75, report_count=2,
        created_at="2026-07-01T10:00:00Z" # Fairly recent
    )
    h2.road_class = "Residential"
    h2.road_importance = 20
    
    h2 = RiskEngine.calculate(h2)
    
    print("\n[Hazard 2] - Expected Medium/Low")
    print(f"Risk Score: {h2.risk_score}, Level: {h2.risk_level}")
    print(f"Requires Assignment: {h2.requires_assignment}")
    print(f"Reason: {h2.risk_reason}")
    print(f"Action: {h2.recommended_action}")

if __name__ == "__main__":
    test_risk_engine()
