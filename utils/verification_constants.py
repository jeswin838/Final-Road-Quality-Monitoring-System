"""
Verification Constants — Phase 8 (Enterprise Verification Engine)
"""

# ─── Verification Statuses ─────────────────────────────────────────────────────
VERIFICATION_STATUS_PENDING = "Verification Pending"
VERIFICATION_STATUS_SCHEDULED = "Inspection Scheduled"
VERIFICATION_STATUS_STARTED = "Inspection Started"
VERIFICATION_STATUS_VERIFIED = "Verified"
VERIFICATION_STATUS_REJECTED = "Rejected"
VERIFICATION_STATUS_REOPENED = "Reopened"

# ─── Verification Results ──────────────────────────────────────────────────────
VERIFICATION_RESULT_PASS = "PASS"
VERIFICATION_RESULT_FAIL = "FAIL"

# ─── Verification Grades ───────────────────────────────────────────────────────
GRADE_EXCELLENT = "Excellent"   # 90+
GRADE_GOOD = "Good"             # 75-90
GRADE_ACCEPTABLE = "Acceptable" # 60-75
GRADE_REJECTED = "Rejected"     # Below 60

# ─── Scoring Weights (Deterministic 100-pt scale) ──────────────────────────────
SCORE_WEIGHT_BEFORE_PHOTO = 20
SCORE_WEIGHT_AFTER_PHOTO = 20
SCORE_WEIGHT_VERIFICATION_PHOTO = 20
SCORE_WEIGHT_GPS = 10
SCORE_WEIGHT_ENGINEER = 10
SCORE_WEIGHT_WORKFLOW = 10
SCORE_WEIGHT_TIMELINE = 10

# ─── Default Verification Reasons ──────────────────────────────────────────────
REASON_PASS_EVIDENCE_COMPLETE = "Repair evidence complete."
REASON_PASS_INSPECTION_SUCCESS = "Engineer inspection successful."
REASON_PASS_GPS_VERIFIED = "GPS verified."
REASON_PASS_CONDITION_ACCEPTABLE = "Road condition acceptable."
REASON_PASS_QUALITY_ACCEPTABLE = "Repair quality acceptable."

REASON_FAIL_MISSING_EVIDENCE = "Missing repair evidence."
REASON_FAIL_AFTER_PHOTO = "After photo unavailable."
REASON_FAIL_GPS_MISMATCH = "GPS mismatch."
REASON_FAIL_INCOMPLETE = "Repair incomplete."
REASON_FAIL_INSPECTION = "Inspection failed."

# ─── Recommendations ───────────────────────────────────────────────────────────
RECOMMENDATION_CLOSE = "Close Hazard"
RECOMMENDATION_FOLLOWUP = "Schedule Follow-up Inspection"
RECOMMENDATION_REWORK = "Immediate Rework Required"
RECOMMENDATION_SUPERVISOR = "Supervisor Review Required"
RECOMMENDATION_CONTRACTOR = "Contractor Review Required"

# ─── Metrics Tags ──────────────────────────────────────────────────────────────
TAG_VERIFY_PASS = "[VERIFY PASS]"
TAG_VERIFY_FAIL = "[VERIFY FAIL]"
TAG_VERIFY_SCORE = "[VERIFY SCORE]"
TAG_VERIFY_GPS = "[VERIFY GPS]"
TAG_VERIFY_PHOTO = "[VERIFY PHOTO]"
TAG_VERIFY_HISTORY = "[VERIFY HISTORY]"
TAG_VERIFY_METRIC = "[VERIFY METRIC]"
