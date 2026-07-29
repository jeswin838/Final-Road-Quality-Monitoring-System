import logging
import datetime
from models.hazard import Hazard
from models.worker import Worker
from repositories.worker_repository import WorkerRepository
from services.assignment_engine import AssignmentEngine
from services.approval_service import ApprovalService
from utils.assignment_db_setup import setup_assignment_db

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')

def seed_workers():
    repo = WorkerRepository()
    
    w1 = Worker(
        worker_id="W-001", employee_code="EMP101", name="John Highway", team="Highway Team Alpha",
        department="Roadways", designation="Senior Technician", phone="555-0101", email="john@muni.com",
        zone="North", district="Central", skills=["Highway Maintenance", "Heavy Repair"], 
        is_on_leave=False, is_online=True, is_emergency_team=True, certifications=["Hazmat"],
        latitude=10.01, longitude=10.01, active_tasks=0, completed_tasks=45, experience_years=5,
        max_daily_tasks=5, today_tasks=0, current_workload=0, 
        vehicle="Heavy Duty Truck", equipment=["Excavator", "Hot Mix", "Traffic Cone"], status="Active",
        created_at=datetime.datetime.now().isoformat(), updated_at=datetime.datetime.now().isoformat()
    )
    
    w2 = Worker(
        worker_id="W-002", employee_code="EMP102", name="Sarah Inspect", team="Inspection Team Beta",
        department="Quality Control", designation="Inspector", phone="555-0102", email="sarah@muni.com",
        zone="South", district="Central", skills=["Inspection", "General Maintenance"], 
        is_on_leave=False, is_online=True, is_emergency_team=False, certifications=[],
        latitude=9.95, longitude=9.95, active_tasks=2, completed_tasks=100, experience_years=3,
        max_daily_tasks=8, today_tasks=2, current_workload=2, 
        vehicle="Bike", equipment=["Camera", "Tablet"], status="Active",
        created_at=datetime.datetime.now().isoformat(), updated_at=datetime.datetime.now().isoformat()
    )
    
    w3 = Worker(
        worker_id="W-003", employee_code="EMP103", name="Mike Local", team="Zone North Local",
        department="Roadways", designation="Technician", phone="555-0103", email="mike@muni.com",
        zone="North", district="Central", skills=["General Maintenance"], 
        is_on_leave=False, is_online=True, is_emergency_team=False, certifications=[],
        latitude=10.03, longitude=10.03, active_tasks=1, completed_tasks=10, experience_years=1,
        max_daily_tasks=5, today_tasks=1, current_workload=1, 
        vehicle="Van", equipment=["Cold Mix"], status="Active",
        created_at=datetime.datetime.now().isoformat(), updated_at=datetime.datetime.now().isoformat()
    )
    
    repo.save_worker(w1)
    repo.save_worker(w2)
    repo.save_worker(w3)
    print("Seeded workers.")

def test_assignment():
    setup_assignment_db()
    seed_workers()
    
    engine = AssignmentEngine()
    approval = ApprovalService()
    
    # Hazard right next to John Highway, needs highway skills
    h1 = Hazard(hazard_id="HAZ-TEST-1", latitude=10.02, longitude=10.02, created_at="2024-01-01T00:00:00Z")
    h1.road_class = "Motorway"
    h1.zone = "North"
    h1.priority = "Emergency"
    
    print("\n--- GENERATING RECOMMENDATIONS ---")
    bundle = engine.generate_recommendations(h1)
    print(f"Engine Version: {bundle.engine_version}")
    
    for i, rec in enumerate(bundle.recommendations):
        print(f"\n[Rank {i+1}] {rec.worker_name} ({rec.worker_id})")
        print(f"  Score  : {rec.recommendation_score}")
        print(f"  Reason : {rec.recommendation_reason}")
        print(f"  ETA    : {rec.recommended_eta} hours")
        print(f"  Vehicle: {rec.recommended_vehicle}")
        print(f"  Equip  : {', '.join(rec.recommended_equipment)}")
        print(f"  Details: {rec.score_breakdown}")
        
    print("\n--- ADMIN APPROVING TOP RECOMMENDATION ---")
    # Admin chooses the first one
    top_rec = bundle.recommendations[0].__dict__
    assignment = approval.approve_recommendation(h1.hazard_id, top_rec)
    
    print(f"Assignment Created! ID: {assignment.assignment_id}")
    print(f"Status: {assignment.status}")
    print(f"Assigned To: {assignment.worker_id}")

if __name__ == "__main__":
    test_assignment()
