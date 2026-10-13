import uuid
import datetime
import threading
from models.assignment import Assignment
from models.assignment_recommendation import AssignmentRecommendation
from repositories.assignment_repository import AssignmentRepository
from repositories.worker_repository import WorkerRepository
from utils.assignment_constants import STATUS_APPROVED

class ApprovalService:
    def __init__(self):
        self.assignment_repo = AssignmentRepository()
        self.worker_repo = WorkerRepository()
        self.lock = threading.Lock()

    def approve_recommendation(self, hazard_id: str, recommendation: dict, admin_id: str = "Admin") -> Assignment:
        """
        Thread-safe persistence of an Admin-approved recommendation.
        """
        with self.lock:
            assignment_id = str(uuid.uuid4())
            now = datetime.datetime.now().isoformat()
            
            assignment = Assignment(
                assignment_id=assignment_id,
                hazard_id=hazard_id,
                worker_id=recommendation.get("worker_id", ""),
                recommended_team=recommendation.get("recommended_team", ""),
                recommended_vehicle=recommendation.get("recommended_vehicle", ""),
                recommended_equipment=recommendation.get("recommended_equipment", []),
                recommended_eta=recommendation.get("recommended_eta", 0.0),
                recommended_distance=recommendation.get("recommended_distance", 0.0),
                recommendation_score=recommendation.get("recommendation_score", 0.0),
                score_breakdown=recommendation.get("score_breakdown", {}),
                recommendation_reason=recommendation.get("recommendation_reason", ""),
                approved_by_admin=True,
                assigned_time=now,
                status=STATUS_APPROVED,
                priority="Unknown", # Fetch from hazard if needed, defaulting for now
                history=[]
            )
            
            self.assignment_repo.save_assignment(assignment)
            
            # Append history
            self.assignment_repo.append_history(
                assignment_id=assignment_id,
                status=STATUS_APPROVED,
                changed_at=now,
                changed_by=admin_id,
                notes=f"Admin approved recommendation with score {assignment.recommendation_score}."
            )
            
            # Update worker workload safely
            worker = self.worker_repo.get_worker(assignment.worker_id)
            if worker:
                worker.current_workload += 1
                self.worker_repo.save_worker(worker)
                
            # Sync to Supabase assignments table so worker dispatch system picks it up
            try:
                from app import supabase
                worker_id = recommendation.get("worker_id", "")
                worker_name = recommendation.get("worker_name", "")
                if worker_id and not worker_name:
                    w = self.worker_repo.get_worker(worker_id)
                    if w:
                        worker_name = w.name
                
                clean_hid = hazard_id
                hazard_source = 'AI'
                if isinstance(hazard_id, str):
                    if hazard_id.startswith('AI-'):
                        clean_hid = hazard_id.replace('AI-', '')
                        hazard_source = 'AI'
                    elif hazard_id.startswith('USER-'):
                        clean_hid = hazard_id.replace('USER-', '')
                        hazard_source = 'USER'
                try:
                    clean_hid = int(clean_hid)
                except (ValueError, TypeError):
                    pass

                supabase.table('assignments').insert({
                    'hazard_id': clean_hid,
                    'hazard_source': hazard_source,
                    'worker_id': worker_id if worker_id else None,
                    'worker_name': worker_name if worker_name else "Assigned Worker",
                    'assigned_by_name': admin_id,
                    'status': 'Assigned',
                    'verification_status': 'Pending',
                    'admin_notes': f"Approved recommendation with score {assignment.recommendation_score}"
                }).execute()
            except Exception as e:
                print("[!] ApprovalService Supabase sync notice:", e)

            return assignment

