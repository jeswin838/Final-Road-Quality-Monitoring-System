"""
Task Service — Phase 7b (Enterprise Hardening)
CRUD + automatic timestamp population + full transaction wrapping.
All state transitions happen inside BEGIN / COMMIT / ROLLBACK.
"""
import uuid
import datetime
import logging
import sqlite3
import os
from typing import Optional, List, Dict

from models.maintenance_task import MaintenanceTask
from repositories.maintenance_repository import MaintenanceRepository
from repositories.history_repository import HistoryRepository
from models.workflow_event import WorkflowEvent
from utils.workflow_constants import (
    STATE_DETECTED, STATE_CLOSED, STATE_REOPENED,
    STATE_TIMESTAMP_MAP, WORKFLOW_VERSION, STATE_EVENT_MAP,
    EVENT_SOURCE, EVENT_VERSION,
)

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'local_db.sqlite')


class TaskService:
    def __init__(self):
        self.repo = MaintenanceRepository()
        self.history_repo = HistoryRepository()

    # ── Task Creation ──────────────────────────────────────────────────────────
    def create_task(
        self,
        hazard_id: str,
        assignment_id: Optional[str] = None,
        created_by: str = "System",
    ) -> MaintenanceTask:
        now = datetime.datetime.now().isoformat()
        task = MaintenanceTask(
            task_id=str(uuid.uuid4()),
            hazard_id=hazard_id,
            assignment_id=assignment_id,
            current_state=STATE_DETECTED,
            workflow_version=WORKFLOW_VERSION,
            row_version=1,
            reopen_count=0,
            created_time=now,
            updated_time=now,
            created_by=created_by,
            last_modified_by=created_by,
        )
        self.repo.save_task(task)
        logger.info(f"[TASK] Created task {task.task_id} for hazard {hazard_id}")
        return task

    def get_task(self, task_id: str) -> Optional[MaintenanceTask]:
        return self.repo.get_task(task_id)

    def get_or_create_task(
        self, hazard_id: str, assignment_id: Optional[str] = None, created_by: str = "System"
    ) -> MaintenanceTask:
        existing = self.repo.get_task_by_hazard(hazard_id)
        if existing:
            return existing
        return self.create_task(hazard_id, assignment_id, created_by)

    # ── Transactional State Transition ────────────────────────────────────────
    def apply_state_transition(
        self,
        task: MaintenanceTask,
        new_state: str,
        changed_by: str = "System",
        actor_type: str = "System",
        remarks: str = "",
        gps_lat: Optional[float] = None,
        gps_lon: Optional[float] = None,
        gps_accuracy: Optional[float] = None,
        photo_before: Optional[str] = None,
        photo_after: Optional[str] = None,
        verification_photo: Optional[str] = None,
        device: Optional[str] = None,
        device_type: Optional[str] = None,
        expected_version: Optional[int] = None,   # for optimistic locking
    ) -> MaintenanceTask:
        """
        Wraps task update + history insert + event insert in one SQLite transaction.
        Raises on any failure; SQLite rolls back automatically.
        """
        now = datetime.datetime.now().isoformat()
        previous_state = task.current_state
        # Use caller-supplied version (pre-read) or fall back to current task value
        lock_version = expected_version if expected_version is not None else task.row_version

        # Mutate task fields
        task.current_state = new_state
        task.updated_time = now
        task.last_modified_by = changed_by

        # Auto-populate the designated timestamp column (only on first entry)
        ts_col = STATE_TIMESTAMP_MAP.get(new_state)
        if ts_col and getattr(task, ts_col, None) is None:
            setattr(task, ts_col, now)

        # Reopen counter
        if new_state == STATE_REOPENED:
            task.reopen_count += 1
            task.last_reopened_at = now

        # Closed time
        if new_state == STATE_CLOSED:
            task.closed_time = now
            task.closed_at = now

        # ── Single transaction ─────────────────────────────────────────────────
        conn = sqlite3.connect(DB_PATH)
        try:
            conn.execute("BEGIN")

            # 1. Optimistic-locked task update
            self.repo.save_task_optimistic(task, lock_version, conn=conn)

            # 2. Append-only history (with hash chain)
            self.history_repo.append(
                task_id=task.task_id,
                previous_state=previous_state,
                new_state=new_state,
                changed_by=changed_by,
                changed_time=now,
                actor_type=actor_type,
                remarks=remarks,
                gps_lat=gps_lat,
                gps_lon=gps_lon,
                gps_accuracy=gps_accuracy,
                photo_before=photo_before,
                photo_after=photo_after,
                verification_photo=verification_photo,
                device=device,
                device_type=device_type,
                conn=conn,
            )

            # 3. Emit workflow event
            event_type = STATE_EVENT_MAP.get(new_state)
            if event_type:
                event = WorkflowEvent(
                    event_id=None,
                    task_id=task.task_id,
                    event_type=event_type,
                    event_time=now,
                    payload=None,
                )
                event.event_source = EVENT_SOURCE    # type: ignore[attr-defined]
                event.event_version = EVENT_VERSION  # type: ignore[attr-defined]
                self.repo.save_event(event, conn=conn)

            conn.commit()
            logger.info(f"[TASK] {task.task_id} -> state={new_state} (row_version={task.row_version})")

        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

        return task

    # ── Kanban ────────────────────────────────────────────────────────────────
    def get_kanban(self) -> Dict[str, List[dict]]:
        """Returns tasks pre-grouped by current_state — no frontend grouping needed."""
        all_tasks = self.repo.get_all_tasks()
        board: Dict[str, List[dict]] = {}
        for t in all_tasks:
            # Exclude computed properties from dict to avoid issues
            d = {
                k: getattr(t, k)
                for k in t.__dataclass_fields__  # type: ignore[attr-defined]
            }
            board.setdefault(t.current_state, []).append(d)
        return board

    # ── Metrics ───────────────────────────────────────────────────────────────
    def get_metrics(self, task: MaintenanceTask) -> Dict[str, Optional[float]]:
        return {
            "travel_duration_minutes":       task.travel_duration,
            "inspection_duration_minutes":   task.inspection_duration,
            "repair_duration_minutes":       task.repair_duration,
            "verification_duration_minutes": task.verification_duration,
            "total_duration_minutes":        task.total_duration,
            "reopen_count":                  task.reopen_count,
        }
