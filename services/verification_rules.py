from typing import Dict, List, Tuple
from utils.verification_constants import (
    VERIFICATION_RESULT_PASS, VERIFICATION_RESULT_FAIL,
    REASON_PASS_EVIDENCE_COMPLETE, REASON_PASS_INSPECTION_SUCCESS,
    REASON_PASS_GPS_VERIFIED, REASON_PASS_CONDITION_ACCEPTABLE,
    REASON_PASS_QUALITY_ACCEPTABLE, REASON_FAIL_MISSING_EVIDENCE,
    REASON_FAIL_AFTER_PHOTO, REASON_FAIL_GPS_MISMATCH,
    REASON_FAIL_INCOMPLETE, REASON_FAIL_INSPECTION,
    RECOMMENDATION_CLOSE, RECOMMENDATION_REWORK,
    GRADE_REJECTED
)

class VerificationRules:
    def evaluate_pass_fail(self, score: int, score_breakdown: Dict[str, int]) -> str:
        if score < 60:
            return VERIFICATION_RESULT_FAIL
        if score_breakdown.get("after_photo", 0) == 0:
            return VERIFICATION_RESULT_FAIL
        if score_breakdown.get("verification_photo", 0) == 0:
            return VERIFICATION_RESULT_FAIL
        if score_breakdown.get("engineer", 0) == 0:
            return VERIFICATION_RESULT_FAIL
        if score_breakdown.get("gps", 0) == 0:
            return VERIFICATION_RESULT_FAIL
        
        return VERIFICATION_RESULT_PASS

    def generate_reason(self, result: str, score_breakdown: Dict[str, int]) -> str:
        reasons = []
        if result == VERIFICATION_RESULT_PASS:
            if score_breakdown.get("after_photo", 0) > 0 and score_breakdown.get("verification_photo", 0) > 0:
                reasons.append(REASON_PASS_EVIDENCE_COMPLETE)
            if score_breakdown.get("engineer", 0) > 0:
                reasons.append(REASON_PASS_INSPECTION_SUCCESS)
            if score_breakdown.get("gps", 0) > 0:
                reasons.append(REASON_PASS_GPS_VERIFIED)
            reasons.append(REASON_PASS_CONDITION_ACCEPTABLE)
            reasons.append(REASON_PASS_QUALITY_ACCEPTABLE)
        else:
            if score_breakdown.get("after_photo", 0) == 0:
                reasons.append(REASON_FAIL_AFTER_PHOTO)
            if score_breakdown.get("verification_photo", 0) == 0:
                reasons.append(REASON_FAIL_MISSING_EVIDENCE)
            if score_breakdown.get("gps", 0) == 0:
                reasons.append(REASON_FAIL_GPS_MISMATCH)
            if score_breakdown.get("engineer", 0) == 0:
                reasons.append(REASON_FAIL_INSPECTION)
            
            if not reasons:
                reasons.append(REASON_FAIL_INCOMPLETE)
        
        return " ".join(reasons)

    def generate_recommendation(self, result: str, score: int) -> str:
        if result == VERIFICATION_RESULT_PASS:
            return RECOMMENDATION_CLOSE
        return RECOMMENDATION_REWORK
