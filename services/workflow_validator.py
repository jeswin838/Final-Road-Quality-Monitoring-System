"""
Workflow Validator — Phase 7b (Enterprise Hardening)
Business-rule guards that run before the state machine is consulted.
"""
import logging
from models.maintenance_task import MaintenanceTask
from utils.workflow_constants import (
    STATE_CANCELLED, STATE_CLOSED, STATE_REOPENED,
    STATE_ASSIGNED, STATE_WORKER_ACCEPTED,
)

logger = logging.getLogger(__name__)


class WorkflowValidationError(Exception):
    """Raised when a business rule prevents the transition."""
    pass


class ConcurrentModificationError(Exception):
    """Raised when a row_version mismatch is detected."""
    pass


def validate_task_exists(task: MaintenanceTask) -> None:
    if task is None:
        raise WorkflowValidationError("[VALIDATION] Task not found.")


def validate_not_terminal(task: MaintenanceTask) -> None:
    """Cancelled tasks cannot be transitioned at all."""
    if task.current_state == STATE_CANCELLED:
        raise WorkflowValidationError(
            f"[VALIDATION] Task {task.task_id} is CANCELLED and cannot be transitioned."
        )


def validate_not_closed(task: MaintenanceTask, to_state: str) -> None:
    """
    Closed tasks may only move to Reopened.
    All other transitions from Closed are blocked at the validator level
    (the state machine also enforces this, but defense-in-depth).
    """
    if task.current_state == STATE_CLOSED and to_state != STATE_REOPENED:
        raise WorkflowValidationError(
            f"[VALIDATION] Task {task.task_id} is CLOSED. "
            f"Only transition to '{STATE_REOPENED}' is permitted."
        )


def validate_assignment_present(task: MaintenanceTask, to_state: str) -> None:
    """
    Transitions into Assigned or Worker Accepted require an assignment_id.
    """
    guarded = {STATE_ASSIGNED, STATE_WORKER_ACCEPTED}
    if to_state in guarded and not task.assignment_id:
        raise WorkflowValidationError(
            f"[VALIDATION] Task {task.task_id} cannot transition to '{to_state}' "
            f"without an assignment_id."
        )


def run_all_validations(task: MaintenanceTask, to_state: str) -> None:
    """Run the full validation suite. Raises on first failure."""
    validate_task_exists(task)
    validate_not_terminal(task)
    validate_not_closed(task, to_state)
    validate_assignment_present(task, to_state)
    logger.debug(f"[VALIDATION] Task {task.task_id} passed all guards for -> '{to_state}'")
