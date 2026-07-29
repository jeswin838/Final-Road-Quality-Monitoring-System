"""
History Repository — Phase 7b (Enterprise Hardening)
Append-only writes to maintenance_history.
UUID primary key. SHA-256 hash chain. Actor/device metadata.
Never deletes. Never updates existing rows.
"""
import sqlite3
import os
import uuid
import hashlib
from typing import Optional, List

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'local_db.sqlite')

_HISTORY_COLUMNS = [
    "history_id", "task_id", "previous_state", "new_state",
    "changed_by", "actor_type", "changed_time", "remarks",
    "gps_lat", "gps_lon", "gps_accuracy",
    "photo_before", "photo_after", "verification_photo",
    "device", "device_type", "previous_hash", "current_hash",
]


def _compute_hash(previous_hash: Optional[str], task_id: str, new_state: str, timestamp: str) -> str:
    raw = f"{previous_hash or ''}{task_id}{new_state}{timestamp}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _get_latest_hash(conn: sqlite3.Connection, task_id: str) -> Optional[str]:
    cursor = conn.execute(
        "SELECT current_hash FROM maintenance_history WHERE task_id=? ORDER BY changed_time DESC LIMIT 1",
        (task_id,)
    )
    row = cursor.fetchone()
    return row[0] if row else None


class HistoryRepository:
    def _conn(self):
        return sqlite3.connect(DB_PATH)

    def append(
        self,
        task_id: str,
        previous_state: Optional[str],
        new_state: str,
        changed_by: str,
        changed_time: str,
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
        conn: Optional[sqlite3.Connection] = None,
    ) -> str:
        """
        Appends a history row within an optional shared connection (for transactions).
        Returns the new history_id (UUID).
        """
        history_id = str(uuid.uuid4())
        own_conn = conn is None
        if own_conn:
            conn = sqlite3.connect(DB_PATH)

        try:
            prev_hash = _get_latest_hash(conn, task_id)
            curr_hash = _compute_hash(prev_hash, task_id, new_state, changed_time)

            conn.execute(
                f"INSERT INTO maintenance_history ({','.join(_HISTORY_COLUMNS)}) "
                f"VALUES ({','.join(['?']*len(_HISTORY_COLUMNS))})",
                (
                    history_id, task_id, previous_state, new_state,
                    changed_by, actor_type, changed_time, remarks,
                    gps_lat, gps_lon, gps_accuracy,
                    photo_before, photo_after, verification_photo,
                    device, device_type, prev_hash, curr_hash,
                )
            )
            if own_conn:
                conn.commit()
        finally:
            if own_conn:
                conn.close()

        return history_id

    def get_history(self, task_id: str) -> List[dict]:
        conn = self._conn()
        try:
            cursor = conn.execute(
                "SELECT * FROM maintenance_history WHERE task_id=? ORDER BY changed_time ASC",
                (task_id,)
            )
            cols = [d[0] for d in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]
        finally:
            conn.close()
