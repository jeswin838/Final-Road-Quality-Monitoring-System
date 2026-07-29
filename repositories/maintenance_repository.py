"""
Maintenance Repository — Phase 7b (Enterprise Hardening)
CRUD for maintenance_tasks and workflow_events.
Supports optimistic locking via row_version.
"""
import sqlite3
import os
import uuid
import json
from typing import Optional, List
from models.maintenance_task import MaintenanceTask
from models.workflow_event import WorkflowEvent
from services.workflow_validator import ConcurrentModificationError

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'local_db.sqlite')

_TASK_COLUMNS = [
    "task_id", "hazard_id", "assignment_id", "maintenance_task_id",
    "current_state", "workflow_version", "row_version",
    "reopen_count", "last_reopened_at",
    "created_time", "updated_time", "created_by", "last_modified_by", "closed_time",
    "assigned_at", "accepted_at", "travel_started_at", "arrived_at",
    "inspection_started_at", "repair_started_at", "temporary_completed_at",
    "repair_completed_at", "verification_started_at", "verified_at", "closed_at",
]


class MaintenanceRepository:
    def _conn(self):
        return sqlite3.connect(DB_PATH)

    # ── Tasks ──────────────────────────────────────────────────────────────────
    def save_task(self, task: MaintenanceTask, conn: Optional[sqlite3.Connection] = None) -> None:
        """Unconditional upsert (used for new tasks)."""
        own_conn = conn is None
        if own_conn:
            conn = sqlite3.connect(DB_PATH)
        try:
            placeholders = ",".join(["?" for _ in _TASK_COLUMNS])
            cols = ",".join(_TASK_COLUMNS)
            values = tuple(getattr(task, c, None) for c in _TASK_COLUMNS)
            conn.execute(
                f"INSERT OR REPLACE INTO maintenance_tasks ({cols}) VALUES ({placeholders})",
                values
            )
            if own_conn:
                conn.commit()
        finally:
            if own_conn:
                conn.close()

    def save_task_optimistic(
        self,
        task: MaintenanceTask,
        expected_version: int,
        conn: Optional[sqlite3.Connection] = None,
    ) -> None:
        """
        Optimistic-locked update. Raises ConcurrentModificationError if
        the row_version in the DB does not match expected_version.
        """
        own_conn = conn is None
        if own_conn:
            conn = sqlite3.connect(DB_PATH)
        try:
            task.row_version = expected_version + 1
            set_clause = ", ".join(f"{c}=?" for c in _TASK_COLUMNS if c != "task_id")
            values = tuple(getattr(task, c, None) for c in _TASK_COLUMNS if c != "task_id")
            cursor = conn.execute(
                f"UPDATE maintenance_tasks SET {set_clause} "
                f"WHERE task_id=? AND row_version=?",
                (*values, task.task_id, expected_version)
            )
            if cursor.rowcount == 0:
                raise ConcurrentModificationError(
                    f"[OPTIMISTIC LOCK] Task {task.task_id} was modified concurrently "
                    f"(expected row_version={expected_version})."
                )
            if own_conn:
                conn.commit()
        finally:
            if own_conn:
                conn.close()

    def get_task(self, task_id: str) -> Optional[MaintenanceTask]:
        conn = self._conn()
        try:
            cursor = conn.execute(
                "SELECT * FROM maintenance_tasks WHERE task_id=?", (task_id,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            cols = [d[0] for d in cursor.description]
            data = dict(zip(cols, row))
            # Only pass fields that MaintenanceTask knows about
            import inspect
            valid_fields = set(inspect.signature(MaintenanceTask.__init__).parameters.keys()) - {'self'}
            filtered = {k: v for k, v in data.items() if k in valid_fields}
            return MaintenanceTask(**filtered)
        finally:
            conn.close()

    def get_task_by_hazard(self, hazard_id: str) -> Optional[MaintenanceTask]:
        conn = self._conn()
        try:
            cursor = conn.execute(
                "SELECT * FROM maintenance_tasks WHERE hazard_id=?", (hazard_id,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            cols = [d[0] for d in cursor.description]
            data = dict(zip(cols, row))
            import inspect
            valid_fields = set(inspect.signature(MaintenanceTask.__init__).parameters.keys()) - {'self'}
            filtered = {k: v for k, v in data.items() if k in valid_fields}
            return MaintenanceTask(**filtered)
        finally:
            conn.close()

    def get_all_tasks(self) -> List[MaintenanceTask]:
        conn = self._conn()
        try:
            cursor = conn.execute("SELECT * FROM maintenance_tasks")
            cols = [d[0] for d in cursor.description]
            rows = cursor.fetchall()
            import inspect
            valid_fields = set(inspect.signature(MaintenanceTask.__init__).parameters.keys()) - {'self'}
            result = []
            for row in rows:
                data = dict(zip(cols, row))
                filtered = {k: v for k, v in data.items() if k in valid_fields}
                result.append(MaintenanceTask(**filtered))
            return result
        finally:
            conn.close()

    # ── Events ─────────────────────────────────────────────────────────────────
    def save_event(self, event: WorkflowEvent, conn: Optional[sqlite3.Connection] = None) -> None:
        own_conn = conn is None
        if own_conn:
            conn = sqlite3.connect(DB_PATH)
        try:
            event_id = str(uuid.uuid4())
            conn.execute(
                "INSERT INTO workflow_events (event_id, task_id, event_type, event_source, event_version, event_time, payload) "
                "VALUES (?,?,?,?,?,?,?)",
                (event_id, event.task_id, event.event_type,
                 getattr(event, 'event_source', None),
                 getattr(event, 'event_version', None),
                 event.event_time, event.payload)
            )
            if own_conn:
                conn.commit()
        finally:
            if own_conn:
                conn.close()

    def get_events(self, task_id: str) -> List[dict]:
        conn = self._conn()
        try:
            cursor = conn.execute(
                "SELECT * FROM workflow_events WHERE task_id=? ORDER BY event_time ASC",
                (task_id,)
            )
            cols = [d[0] for d in cursor.description]
            return [dict(zip(cols, r)) for r in cursor.fetchall()]
        finally:
            conn.close()
