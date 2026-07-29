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
                
            return assignment
