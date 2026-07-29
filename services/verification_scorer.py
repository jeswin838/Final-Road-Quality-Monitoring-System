from typing import Dict, Any, Tuple
from models.verification import Verification
from utils.verification_constants import (
    SCORE_WEIGHT_BEFORE_PHOTO, SCORE_WEIGHT_AFTER_PHOTO,
    SCORE_WEIGHT_VERIFICATION_PHOTO, SCORE_WEIGHT_GPS,
    SCORE_WEIGHT_ENGINEER, SCORE_WEIGHT_WORKFLOW, SCORE_WEIGHT_TIMELINE,
    GRADE_EXCELLENT, GRADE_GOOD, GRADE_ACCEPTABLE, GRADE_REJECTED
)

class VerificationScorer:
    def score(self, verif: Verification) -> Tuple[int, str, Dict[str, int]]:
        score = 0
        breakdown = {}

        if verif.before_photo:
            score += SCORE_WEIGHT_BEFORE_PHOTO
            breakdown["before_photo"] = SCORE_WEIGHT_BEFORE_PHOTO
        else:
            breakdown["before_photo"] = 0

        if verif.after_photo:
            score += SCORE_WEIGHT_AFTER_PHOTO
            breakdown["after_photo"] = SCORE_WEIGHT_AFTER_PHOTO
        else:
            breakdown["after_photo"] = 0

        if verif.verification_photo:
            score += SCORE_WEIGHT_VERIFICATION_PHOTO
            breakdown["verification_photo"] = SCORE_WEIGHT_VERIFICATION_PHOTO
        else:
            breakdown["verification_photo"] = 0

        if verif.gps_lat is not None and verif.gps_lon is not None:
            score += SCORE_WEIGHT_GPS
            breakdown["gps"] = SCORE_WEIGHT_GPS
        else:
            breakdown["gps"] = 0

        if verif.engineer_name:
            score += SCORE_WEIGHT_ENGINEER
            breakdown["engineer"] = SCORE_WEIGHT_ENGINEER
        else:
            breakdown["engineer"] = 0

        # Since validate_workflow_state must pass for scoring to occur, workflow is always full points
        score += SCORE_WEIGHT_WORKFLOW
        breakdown["workflow"] = SCORE_WEIGHT_WORKFLOW

        # Similarly, assume timeline is correct if workflow is correct
        score += SCORE_WEIGHT_TIMELINE
        breakdown["timeline"] = SCORE_WEIGHT_TIMELINE

        grade = self._calculate_grade(score)
        return score, grade, breakdown

    def _calculate_grade(self, score: int) -> str:
        if score >= 90:
            return GRADE_EXCELLENT
        elif score >= 75:
            return GRADE_GOOD
        elif score >= 60:
            return GRADE_ACCEPTABLE
        else:
            return GRADE_REJECTED
