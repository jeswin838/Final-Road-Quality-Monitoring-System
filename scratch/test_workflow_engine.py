"""
Workflow Engine Integration Tests — Phase 7
Exercises the full lifecycle including illegal-transition rejection.
"""
import logging
from utils.workflow_db_setup import setup_workflow_db
from services.maintenance_workflow_engine import MaintenanceWorkflowEngine
from services.state_machine import IllegalTransitionError
from services.workflow_validator import WorkflowValidationError
from utils.workflow_constants import (
    STATE_VERIFIED, STATE_PENDING_ASSIGNMENT,
    STATE_ASSIGNMENT_RECOMMENDED, STATE_ASSIGNMENT_APPROVED,
    STATE_ASSIGNED, STATE_WORKER_ACCEPTED, STATE_TRAVELLING,
    STATE_ARRIVED, STATE_INSPECTION_STARTED, STATE_REPAIR_STARTED,
    STATE_REPAIR_COMPLETED, STATE_VERIFICATION_PENDING,
    STATE_REPAIR_VERIFIED, STATE_CLOSED, STATE_REOPENED,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


def print_divider(label=""):
    print(f"\n{'='*50} {label}")


def test_full_lifecycle():
    print_divider("SETUP")
    setup_workflow_db()
    engine = MaintenanceWorkflowEngine()

    import time
    run_id = str(int(time.time()))  # unique per run

    print_divider("CREATE TASK")
    task = engine.create_task(f"HAZ-WF-{run_id}-1", assignment_id="ASSIGN-001", created_by="Admin")
    print(f"Task created: {task.task_id}  state={task.current_state}")

    # Walk through the full happy path
    steps = [
        (STATE_VERIFIED,               "Inspector"),
        (STATE_PENDING_ASSIGNMENT,     "System"),
        (STATE_ASSIGNMENT_RECOMMENDED, "AssignmentEngine"),
        (STATE_ASSIGNMENT_APPROVED,    "Admin"),
        (STATE_ASSIGNED,               "Admin"),
        (STATE_WORKER_ACCEPTED,        "Worker-W001"),
        (STATE_TRAVELLING,             "Worker-W001"),
        (STATE_ARRIVED,                "Worker-W001"),
        (STATE_INSPECTION_STARTED,     "Worker-W001"),
        (STATE_REPAIR_STARTED,         "Worker-W001"),
        (STATE_REPAIR_COMPLETED,       "Worker-W001"),
        (STATE_VERIFICATION_PENDING,   "Worker-W001"),
        (STATE_REPAIR_VERIFIED,         "QA-Engineer"),
        (STATE_CLOSED,                 "Admin"),
    ]

    print_divider("HAPPY PATH")
    for new_state, actor in steps:
        task = engine.transition(task.task_id, new_state, changed_by=actor)
        print(f"  OK  {task.current_state:<28}  by {actor}")

    print_divider("HISTORY LOG")
    history = engine.get_history(task.task_id)
    for h in history:
        prev = h.get('previous_state') or '-'
        print(f"  [{h['changed_time'][:19]}]  {prev:<28} -> {h['new_state']}")

    print_divider("KANBAN BOARD")
    kanban = engine.get_kanban()
    for col, tasks in kanban.items():
        print(f"  [{col}]: {len(tasks)} task(s)")

    print_divider("ILLEGAL TRANSITION: Detected -> Closed")
    task2 = engine.create_task(f"HAZ-WF-{run_id}-2", created_by="System")
    try:
        engine.transition(task2.task_id, STATE_CLOSED, changed_by="BadActor")
        print("  [FAIL] SHOULD HAVE RAISED -- test FAILED")
    except IllegalTransitionError as e:
        print(f"  [PASS] Correctly rejected: {e}")

    print_divider("ILLEGAL: CANCELLED task cannot transition")
    from utils.workflow_constants import STATE_CANCELLED
    task3 = engine.create_task(f"HAZ-WF-{run_id}-3", created_by="System")
    engine.transition(task3.task_id, STATE_VERIFIED, changed_by="Admin")
    engine.transition(task3.task_id, STATE_PENDING_ASSIGNMENT, changed_by="Admin")
    engine.transition(task3.task_id, STATE_CANCELLED, changed_by="Admin")
    try:
        engine.transition(task3.task_id, STATE_VERIFIED, changed_by="BadActor")
        print("  [FAIL] SHOULD HAVE RAISED -- test FAILED")
    except WorkflowValidationError as e:
        print(f"  [PASS] Correctly rejected: {e}")

    print_divider("DONE")
    print("All tests passed.")


if __name__ == "__main__":
    test_full_lifecycle()
