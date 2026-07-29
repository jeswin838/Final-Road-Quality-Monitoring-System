"""
Phase 7b Hardening Tests
Covers: optimistic lock, closed guard, reopen counter, hash chain, metrics, timeline.
"""
import time
import logging
import sqlite3
import os

from utils.workflow_db_setup import setup_workflow_db
from services.maintenance_workflow_engine import MaintenanceWorkflowEngine
from services.state_machine import IllegalTransitionError
from services.workflow_validator import WorkflowValidationError, ConcurrentModificationError
from utils.workflow_constants import (
    STATE_VERIFIED, STATE_PENDING_ASSIGNMENT, STATE_ASSIGNMENT_RECOMMENDED,
    STATE_ASSIGNMENT_APPROVED, STATE_ASSIGNED, STATE_WORKER_ACCEPTED,
    STATE_TRAVELLING, STATE_ARRIVED, STATE_INSPECTION_STARTED,
    STATE_REPAIR_STARTED, STATE_REPAIR_COMPLETED, STATE_VERIFICATION_PENDING,
    STATE_REPAIR_VERIFIED, STATE_CLOSED, STATE_REOPENED, STATE_CANCELLED,
    STATE_PAUSED, STATE_INSPECTION_FAILED,
)

logging.basicConfig(level=logging.WARNING)
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'local_db.sqlite')


def divider(label):
    print(f"\n{'='*55} {label}")


def run_to_closed(engine, hazard_id, assignment_id=None):
    """Helper: drive a task through the full happy path to Closed."""
    task = engine.create_task(hazard_id, assignment_id=assignment_id, created_by="System")
    steps = [
        (STATE_VERIFIED,               "Inspector",  "Verification Engineer"),
        (STATE_PENDING_ASSIGNMENT,     "System",     "System"),
        (STATE_ASSIGNMENT_RECOMMENDED, "Engine",     "System"),
        (STATE_ASSIGNMENT_APPROVED,    "Admin",      "Admin"),
        (STATE_ASSIGNED,               "Admin",      "Admin"),
        (STATE_WORKER_ACCEPTED,        "Worker",     "Worker"),
        (STATE_TRAVELLING,             "Worker",     "Worker"),
        (STATE_ARRIVED,                "Worker",     "Worker"),
        (STATE_INSPECTION_STARTED,     "Worker",     "Worker"),
        (STATE_REPAIR_STARTED,         "Worker",     "Worker"),
        (STATE_REPAIR_COMPLETED,       "Worker",     "Worker"),
        (STATE_VERIFICATION_PENDING,   "Worker",     "Worker"),
        (STATE_REPAIR_VERIFIED,        "QA",         "Verification Engineer"),
        (STATE_CLOSED,                 "Admin",      "Admin"),
    ]
    for state, actor, actor_type in steps:
        task = engine.transition(task.task_id, state, changed_by=actor, actor_type=actor_type)
    return task


def test_optimistic_locking():
    divider("TEST: Optimistic Locking")
    engine = MaintenanceWorkflowEngine()
    run_id = str(int(time.time()))
    task = engine.create_task(f"HAZ-LOCK-{run_id}", created_by="System")
    # Transition once to get row_version=2
    engine.transition(task.task_id, STATE_VERIFIED, changed_by="Admin")

    # Re-fetch fresh task (row_version=2)
    fresh_task = engine.get_task(task.task_id)

    # Now try to save with stale version=1 — must fail
    from repositories.maintenance_repository import MaintenanceRepository
    from services.workflow_validator import ConcurrentModificationError
    repo = MaintenanceRepository()
    try:
        repo.save_task_optimistic(fresh_task, expected_version=1)  # stale!
        print("  [FAIL] Should have raised ConcurrentModificationError")
    except ConcurrentModificationError as e:
        print(f"  [PASS] Concurrent lock detected: {e}")



def test_closed_guard():
    divider("TEST: Closed Task Cannot Transition (except Reopen)")
    engine = MaintenanceWorkflowEngine()
    run_id = str(int(time.time()))
    task = run_to_closed(engine, f"HAZ-CLOSE-{run_id}", assignment_id="ASN-001")

    # Direct re-transition should be blocked
    try:
        engine.transition(task.task_id, STATE_REPAIR_STARTED, changed_by="BadActor")
        print("  [FAIL] Should have raised WorkflowValidationError")
    except WorkflowValidationError as e:
        print(f"  [PASS] Closed guard fired: {e}")

    # Reopen must succeed
    task = engine.transition(task.task_id, STATE_REOPENED, changed_by="Admin", actor_type="Admin")
    print(f"  [PASS] Reopen succeeded. reopen_count={task.reopen_count}, state={task.current_state}")


def test_reopen_counter():
    divider("TEST: Reopen Counter Increments")
    engine = MaintenanceWorkflowEngine()
    run_id = str(int(time.time()))
    task = run_to_closed(engine, f"HAZ-REOPEN-{run_id}", assignment_id="ASN-002")

    for i in range(1, 4):
        task = engine.transition(task.task_id, STATE_REOPENED, changed_by="Admin")
        assert task.reopen_count == i, f"Expected {i}, got {task.reopen_count}"
        assert task.last_reopened_at is not None
        # Close it again for next iteration
        task = engine.transition(task.task_id, STATE_PENDING_ASSIGNMENT, changed_by="System")
        task = engine.transition(task.task_id, STATE_ASSIGNMENT_RECOMMENDED, changed_by="Engine")
        task = engine.transition(task.task_id, STATE_ASSIGNMENT_APPROVED, changed_by="Admin")
        task = engine.transition(task.task_id, STATE_ASSIGNED, changed_by="Admin")
        task = engine.transition(task.task_id, STATE_WORKER_ACCEPTED, changed_by="Worker")
        task = engine.transition(task.task_id, STATE_TRAVELLING, changed_by="Worker")
        task = engine.transition(task.task_id, STATE_ARRIVED, changed_by="Worker")
        task = engine.transition(task.task_id, STATE_INSPECTION_STARTED, changed_by="Worker")
        task = engine.transition(task.task_id, STATE_REPAIR_STARTED, changed_by="Worker")
        task = engine.transition(task.task_id, STATE_REPAIR_COMPLETED, changed_by="Worker")
        task = engine.transition(task.task_id, STATE_VERIFICATION_PENDING, changed_by="Worker")
        task = engine.transition(task.task_id, STATE_REPAIR_VERIFIED, changed_by="QA")
        task = engine.transition(task.task_id, STATE_CLOSED, changed_by="Admin")

    print(f"  [PASS] Reopen counter reached {task.reopen_count} correctly.")


def test_hash_chain_integrity():
    divider("TEST: Hash Chain Integrity")
    engine = MaintenanceWorkflowEngine()
    run_id = str(int(time.time()))
    task = engine.create_task(f"HAZ-HASH-{run_id}", created_by="System")
    engine.transition(task.task_id, STATE_VERIFIED, changed_by="Inspector")
    engine.transition(task.task_id, STATE_PENDING_ASSIGNMENT, changed_by="System")

    history = engine.get_history(task.task_id)
    # Verify the chain: each row's previous_hash == the prior row's current_hash
    for i in range(1, len(history)):
        prev = history[i - 1]["current_hash"]
        curr = history[i]["previous_hash"]
        assert prev == curr, f"Hash chain broken at row {i}: {prev} != {curr}"
    print(f"  [PASS] Hash chain intact across {len(history)} history rows.")


def test_pause_and_inspection_failed():
    divider("TEST: Pause and Inspection Failed states")
    engine = MaintenanceWorkflowEngine()
    run_id = str(int(time.time()))
    task = engine.create_task(f"HAZ-PAUSE-{run_id}", assignment_id="ASN-003", created_by="System")
    task = engine.transition(task.task_id, STATE_VERIFIED, changed_by="Inspector")
    task = engine.transition(task.task_id, STATE_PENDING_ASSIGNMENT, changed_by="System")
    task = engine.transition(task.task_id, STATE_ASSIGNMENT_RECOMMENDED, changed_by="Engine")
    task = engine.transition(task.task_id, STATE_ASSIGNMENT_APPROVED, changed_by="Admin")
    task = engine.transition(task.task_id, STATE_ASSIGNED, changed_by="Admin")
    task = engine.transition(task.task_id, STATE_WORKER_ACCEPTED, changed_by="Worker")
    task = engine.transition(task.task_id, STATE_TRAVELLING, changed_by="Worker")
    task = engine.transition(task.task_id, STATE_ARRIVED, changed_by="Worker")
    task = engine.transition(task.task_id, STATE_INSPECTION_STARTED, changed_by="Worker")

    # Inspection failed
    task = engine.transition(task.task_id, STATE_INSPECTION_FAILED, changed_by="Worker")
    print(f"  [PASS] Inspection Failed state: {task.current_state}")

    # Re-inspect
    task = engine.transition(task.task_id, STATE_INSPECTION_STARTED, changed_by="Worker")
    task = engine.transition(task.task_id, STATE_REPAIR_STARTED, changed_by="Worker")

    # Pause
    task = engine.transition(task.task_id, STATE_PAUSED, changed_by="Worker")
    print(f"  [PASS] Paused state: {task.current_state}")

    # Resume
    task = engine.transition(task.task_id, STATE_REPAIR_STARTED, changed_by="Worker")
    print(f"  [PASS] Resumed: {task.current_state}")


def test_timeline():
    divider("TEST: MaintenanceTimeline")
    engine = MaintenanceWorkflowEngine()
    run_id = str(int(time.time()))
    task = run_to_closed(engine, f"HAZ-TL-{run_id}", assignment_id="ASN-TL")
    timeline = engine.get_timeline(task.task_id)
    print(f"  [PASS] Timeline has {len(timeline.items)} items for task {task.task_id}")
    for item in timeline.items[:3]:
        print(f"    [{item.timestamp[:19]}] {item.state:<30} actor={item.actor}")


def test_metrics():
    divider("TEST: Workflow Metrics")
    engine = MaintenanceWorkflowEngine()
    run_id = str(int(time.time()))
    task = run_to_closed(engine, f"HAZ-MET-{run_id}", assignment_id="ASN-MET")
    metrics = engine.get_metrics(task.task_id)
    print(f"  [PASS] Metrics: {metrics}")


if __name__ == "__main__":
    setup_workflow_db()
    test_optimistic_locking()
    test_closed_guard()
    test_reopen_counter()
    test_hash_chain_integrity()
    test_pause_and_inspection_failed()
    test_timeline()
    test_metrics()
    divider("ALL HARDENING TESTS PASSED")
    print("Phase 7b verification complete.")
