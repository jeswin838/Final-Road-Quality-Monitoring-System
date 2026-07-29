from models.maintenance_task import MaintenanceTask
from utils.workflow_constants import STATE_REPAIR_COMPLETED, STATE_VERIFICATION_PENDING
from models.verification import Verification
from repositories.verification_repository import VerificationRepository

class VerificationError(Exception):
    pass

class VerificationValidator:
    def __init__(self):
        self.repo = VerificationRepository()

    def validate_workflow_state(self, task: MaintenanceTask) -> None:
        allowed_states = {STATE_REPAIR_COMPLETED, STATE_VERIFICATION_PENDING}
        if task.current_state not in allowed_states:
            raise VerificationError(f"Task {task.task_id} is in state {task.current_state}, which cannot be verified.")

    def validate_not_duplicate(self, task_id: str) -> None:
        existing = self.repo.get_by_task(task_id)
        if existing and existing.verification_result is not None:
            raise VerificationError(f"Task {task_id} already has a completed verification.")

    def validate_mandatory_fields(self, verif: Verification) -> None:
        missing = []
        if not verif.after_photo:
            missing.append("after_photo")
        if not verif.verification_photo:
            missing.append("verification_photo")
        if not verif.engineer_name:
            missing.append("engineer_name")
        if verif.gps_lat is None or verif.gps_lon is None:
            missing.append("gps")
            
        if missing:
            raise VerificationError(f"Verification context missing mandatory fields: {', '.join(missing)}")
