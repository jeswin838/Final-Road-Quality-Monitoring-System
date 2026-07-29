"""
State Machine — Phase 7b (Enterprise Hardening)
Strict directed graph of allowed workflow transitions.
Any unlisted pair raises IllegalTransitionError.
"""
from utils.workflow_constants import (
    STATE_DETECTED, STATE_VERIFIED, STATE_PENDING_ASSIGNMENT,
    STATE_ASSIGNMENT_RECOMMENDED, STATE_ASSIGNMENT_APPROVED,
    STATE_ASSIGNED, STATE_WORKER_ACCEPTED, STATE_TRAVELLING,
    STATE_ARRIVED, STATE_INSPECTION_STARTED, STATE_INSPECTION_FAILED,
    STATE_REPAIR_STARTED, STATE_PAUSED, STATE_TEMPORARY_REPAIR,
    STATE_REPAIR_COMPLETED, STATE_VERIFICATION_PENDING,
    STATE_REPAIR_VERIFIED, STATE_CLOSED,
    STATE_REJECTED, STATE_CANCELLED, STATE_REOPENED, STATE_ESCALATED,
    STATE_WAITING_MATERIALS, STATE_WAITING_TRAFFIC,
    STATE_WAITING_CONTRACTOR, STATE_WEATHER_DELAY,
)


class IllegalTransitionError(Exception):
    """Raised when a requested state transition is not in the allowed graph."""
    pass


# Directed adjacency list — every permitted transition listed explicitly
TRANSITIONS: dict[str, list[str]] = {
    STATE_DETECTED: [
        STATE_VERIFIED,
        STATE_PENDING_ASSIGNMENT,
        STATE_CANCELLED,
        STATE_ESCALATED,
    ],
    STATE_VERIFIED: [
        STATE_PENDING_ASSIGNMENT,
        STATE_CANCELLED,
        STATE_ESCALATED,
    ],
    STATE_PENDING_ASSIGNMENT: [
        STATE_ASSIGNMENT_RECOMMENDED,
        STATE_CANCELLED,
        STATE_ESCALATED,
    ],
    STATE_ASSIGNMENT_RECOMMENDED: [
        STATE_ASSIGNMENT_APPROVED,
        STATE_REJECTED,
        STATE_CANCELLED,
        STATE_ESCALATED,
    ],
    STATE_ASSIGNMENT_APPROVED: [
        STATE_ASSIGNED,
        STATE_CANCELLED,
        STATE_ESCALATED,
    ],
    STATE_ASSIGNED: [
        STATE_WORKER_ACCEPTED,
        STATE_REJECTED,
        STATE_CANCELLED,
        STATE_ESCALATED,
    ],
    STATE_WORKER_ACCEPTED: [
        STATE_TRAVELLING,
        STATE_CANCELLED,
        STATE_ESCALATED,
    ],
    STATE_TRAVELLING: [
        STATE_ARRIVED,
        STATE_WEATHER_DELAY,
        STATE_ESCALATED,
    ],
    STATE_ARRIVED: [
        STATE_INSPECTION_STARTED,
        STATE_WAITING_MATERIALS,
        STATE_WAITING_TRAFFIC,
        STATE_WAITING_CONTRACTOR,
        STATE_ESCALATED,
    ],
    STATE_INSPECTION_STARTED: [
        STATE_REPAIR_STARTED,
        STATE_INSPECTION_FAILED,
        STATE_WAITING_MATERIALS,
        STATE_ESCALATED,
    ],
    STATE_INSPECTION_FAILED: [
        STATE_INSPECTION_STARTED,   # re-inspect
        STATE_WAITING_MATERIALS,
        STATE_ESCALATED,
        STATE_CANCELLED,
    ],
    STATE_REPAIR_STARTED: [
        STATE_PAUSED,
        STATE_TEMPORARY_REPAIR,
        STATE_REPAIR_COMPLETED,
        STATE_WAITING_MATERIALS,
        STATE_WEATHER_DELAY,
        STATE_ESCALATED,
    ],
    STATE_PAUSED: [
        STATE_REPAIR_STARTED,       # resume
        STATE_ESCALATED,
        STATE_CANCELLED,
    ],
    STATE_TEMPORARY_REPAIR: [
        STATE_REPAIR_STARTED,
        STATE_REPAIR_COMPLETED,
        STATE_ESCALATED,
    ],
    STATE_REPAIR_COMPLETED: [
        STATE_VERIFICATION_PENDING,
        STATE_ESCALATED,
    ],
    STATE_VERIFICATION_PENDING: [
        STATE_REPAIR_VERIFIED,
        STATE_REPAIR_STARTED,       # verification failed → rework
        STATE_ESCALATED,
    ],
    STATE_REPAIR_VERIFIED: [
        STATE_CLOSED,
        STATE_ESCALATED,
    ],
    # ── Closed: only re-open path allowed ─────────────────────────────────────
    STATE_CLOSED: [
        STATE_REOPENED,
    ],
    STATE_REOPENED: [
        STATE_PENDING_ASSIGNMENT,
        STATE_REPAIR_STARTED,
        STATE_ESCALATED,
    ],
    STATE_ESCALATED: [
        STATE_PENDING_ASSIGNMENT,
        STATE_ASSIGNED,
        STATE_CANCELLED,
        STATE_CLOSED,
    ],
    # ── Holding states ─────────────────────────────────────────────────────────
    STATE_WAITING_MATERIALS: [
        STATE_REPAIR_STARTED,
        STATE_INSPECTION_STARTED,
        STATE_ESCALATED,
        STATE_CANCELLED,
    ],
    STATE_WAITING_TRAFFIC: [
        STATE_ARRIVED,
        STATE_ESCALATED,
        STATE_CANCELLED,
    ],
    STATE_WAITING_CONTRACTOR: [
        STATE_ARRIVED,
        STATE_ESCALATED,
        STATE_CANCELLED,
    ],
    STATE_WEATHER_DELAY: [
        STATE_TRAVELLING,
        STATE_REPAIR_STARTED,
        STATE_ESCALATED,
        STATE_CANCELLED,
    ],
    STATE_REJECTED: [
        STATE_PENDING_ASSIGNMENT,
        STATE_CANCELLED,
    ],
    # Terminal — no transitions permitted
    STATE_CANCELLED: [],
}


def validate_transition(from_state: str, to_state: str) -> None:
    """
    Validates the transition is in the allowed graph.
    Raises IllegalTransitionError if not.
    """
    allowed = TRANSITIONS.get(from_state)
    if allowed is None:
        raise IllegalTransitionError(
            f"[STATE MACHINE] Unknown source state: '{from_state}'"
        )
    if to_state not in allowed:
        raise IllegalTransitionError(
            f"[STATE MACHINE] Transition '{from_state}' -> '{to_state}' is NOT allowed. "
            f"Allowed: {allowed}"
        )


def get_allowed_transitions(from_state: str) -> list[str]:
    return TRANSITIONS.get(from_state, [])
