"""
Workflow Constants — Phase 7b (Enterprise Hardening)
All state names, event types, actor types, device types, timestamp column mappings.
Never compare raw strings elsewhere — always import from here.
"""

# ─── States ───────────────────────────────────────────────────────────────────
STATE_DETECTED              = "Detected"
STATE_VERIFIED              = "Verified"
STATE_PENDING_ASSIGNMENT    = "Pending Assignment"
STATE_ASSIGNMENT_RECOMMENDED = "Assignment Recommended"
STATE_ASSIGNMENT_APPROVED   = "Assignment Approved"
STATE_ASSIGNED              = "Assigned"
STATE_WORKER_ACCEPTED       = "Worker Accepted"
STATE_TRAVELLING            = "Travelling"
STATE_ARRIVED               = "Arrived On Site"
STATE_INSPECTION_STARTED    = "Inspection Started"
STATE_INSPECTION_FAILED     = "Inspection Failed"
STATE_REPAIR_STARTED        = "Repair Started"
STATE_PAUSED                = "Paused"
STATE_TEMPORARY_REPAIR      = "Temporary Repair"
STATE_REPAIR_COMPLETED      = "Repair Completed"
STATE_VERIFICATION_PENDING  = "Verification Pending"
STATE_REPAIR_VERIFIED       = "Repair Verified"
STATE_CLOSED                = "Closed"

# Optional / exception states
STATE_REJECTED              = "Rejected"
STATE_CANCELLED             = "Cancelled"
STATE_REOPENED              = "Reopened"
STATE_ESCALATED             = "Escalated"
STATE_WAITING_MATERIALS     = "Waiting for Materials"
STATE_WAITING_TRAFFIC       = "Waiting for Traffic Police"
STATE_WAITING_CONTRACTOR    = "Waiting for Contractor"
STATE_WEATHER_DELAY         = "Weather Delay"

# Terminal states — no transitions allowed out (except CLOSED → REOPENED)
TERMINAL_STATES = {STATE_CANCELLED}
CLOSED_STATE    = STATE_CLOSED

# ─── Events ───────────────────────────────────────────────────────────────────
EVENT_TASK_CREATED           = "TASK_CREATED"
EVENT_TASK_VERIFIED          = "TASK_VERIFIED"
EVENT_TASK_ASSIGNED          = "TASK_ASSIGNED"
EVENT_TASK_ACCEPTED          = "TASK_ACCEPTED"
EVENT_TASK_TRAVEL_STARTED    = "TASK_TRAVEL_STARTED"
EVENT_WORKER_ARRIVED         = "WORKER_ARRIVED"
EVENT_INSPECTION_STARTED     = "INSPECTION_STARTED"
EVENT_INSPECTION_FAILED      = "INSPECTION_FAILED"
EVENT_TASK_REPAIR_STARTED    = "TASK_REPAIR_STARTED"
EVENT_TASK_PAUSED            = "TASK_PAUSED"
EVENT_TASK_RESUMED           = "TASK_RESUMED"
EVENT_WORKER_COMPLETED       = "WORKER_COMPLETED"
EVENT_VERIFICATION_REQUIRED  = "VERIFICATION_REQUIRED"
EVENT_TASK_VERIFIED_FINAL    = "TASK_VERIFIED_FINAL"
EVENT_TASK_CLOSED            = "TASK_CLOSED"
EVENT_TASK_REOPENED          = "TASK_REOPENED"
EVENT_TASK_ESCALATED         = "TASK_ESCALATED"
EVENT_TASK_CANCELLED         = "TASK_CANCELLED"

EVENT_VERSION = "1.0"
EVENT_SOURCE  = "MaintenanceWorkflowEngine"

# ─── Actor Types ──────────────────────────────────────────────────────────────
ACTOR_ADMIN             = "Admin"
ACTOR_WORKER            = "Worker"
ACTOR_SYSTEM            = "System"
ACTOR_QA_ENGINEER       = "Verification Engineer"
ACTOR_CITIZEN           = "Citizen"

ACTOR_TYPES = {ACTOR_ADMIN, ACTOR_WORKER, ACTOR_SYSTEM, ACTOR_QA_ENGINEER, ACTOR_CITIZEN}

# ─── Device Types ─────────────────────────────────────────────────────────────
DEVICE_ANDROID  = "android"
DEVICE_WEB      = "web"
DEVICE_TABLET   = "tablet"
DEVICE_DESKTOP  = "desktop"
DEVICE_TYPES    = {DEVICE_ANDROID, DEVICE_WEB, DEVICE_TABLET, DEVICE_DESKTOP}

# ─── Timestamp Columns ────────────────────────────────────────────────────────
# Maps each state to the DB column auto-populated on first entry
STATE_TIMESTAMP_MAP = {
    STATE_ASSIGNED:             "assigned_at",
    STATE_WORKER_ACCEPTED:      "accepted_at",
    STATE_TRAVELLING:           "travel_started_at",
    STATE_ARRIVED:              "arrived_at",
    STATE_INSPECTION_STARTED:   "inspection_started_at",
    STATE_REPAIR_STARTED:       "repair_started_at",
    STATE_TEMPORARY_REPAIR:     "temporary_completed_at",
    STATE_REPAIR_COMPLETED:     "repair_completed_at",
    STATE_VERIFICATION_PENDING: "verification_started_at",
    STATE_REPAIR_VERIFIED:      "verified_at",
    STATE_CLOSED:               "closed_at",
}

# ─── Event Map ────────────────────────────────────────────────────────────────
STATE_EVENT_MAP = {
    STATE_DETECTED:              EVENT_TASK_CREATED,
    STATE_ASSIGNED:              EVENT_TASK_ASSIGNED,
    STATE_WORKER_ACCEPTED:       EVENT_TASK_ACCEPTED,
    STATE_TRAVELLING:            EVENT_TASK_TRAVEL_STARTED,
    STATE_ARRIVED:               EVENT_WORKER_ARRIVED,
    STATE_INSPECTION_STARTED:    EVENT_INSPECTION_STARTED,
    STATE_INSPECTION_FAILED:     EVENT_INSPECTION_FAILED,
    STATE_REPAIR_STARTED:        EVENT_TASK_REPAIR_STARTED,
    STATE_PAUSED:                EVENT_TASK_PAUSED,
    STATE_REPAIR_COMPLETED:      EVENT_WORKER_COMPLETED,
    STATE_VERIFICATION_PENDING:  EVENT_VERIFICATION_REQUIRED,
    STATE_REPAIR_VERIFIED:       EVENT_TASK_VERIFIED_FINAL,
    STATE_CLOSED:                EVENT_TASK_CLOSED,
    STATE_REOPENED:              EVENT_TASK_REOPENED,
    STATE_ESCALATED:             EVENT_TASK_ESCALATED,
    STATE_CANCELLED:             EVENT_TASK_CANCELLED,
}

WORKFLOW_VERSION = "1.0"
