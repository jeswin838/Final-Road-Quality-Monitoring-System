from dataclasses import dataclass, field
from typing import Optional
from utils.verification_constants import VERIFICATION_RESULT_PASS

@dataclass
class Verification:
    verification_id: str
    task_id: str
    hazard_id: str
    assignment_id: Optional[str] = None
    verified_by: Optional[str] = None
    engineer_name: Optional[str] = None
    engineer_department: Optional[str] = None
    verification_status: str = "Verification Pending"
    verification_result: Optional[str] = None
    verification_reason: Optional[str] = None
    verification_notes: Optional[str] = None
    before_photo: Optional[str] = None
    after_photo: Optional[str] = None
    verification_photo: Optional[str] = None
    gps_lat: Optional[float] = None
    gps_lon: Optional[float] = None
    gps_accuracy: Optional[float] = None
    verified_time: Optional[str] = None
    verification_duration: Optional[float] = None
    verification_score: Optional[int] = None
    verification_grade: Optional[str] = None
    recommendation: Optional[str] = None
    remarks: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @property
    def is_passed(self) -> bool:
        return self.verification_result == VERIFICATION_RESULT_PASS
