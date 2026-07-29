import sqlite3
import os
import uuid
import datetime
from typing import Optional, List, Dict, Any
from models.verification import Verification

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'local_db.sqlite')

_VERIF_COLUMNS = [
    "verification_id", "task_id", "hazard_id", "assignment_id",
    "verified_by", "engineer_name", "engineer_department",
    "verification_status", "verification_result", "verification_reason",
    "verification_notes", "before_photo", "after_photo", "verification_photo",
    "gps_lat", "gps_lon", "gps_accuracy", "verified_time",
    "verification_duration", "verification_score", "verification_grade",
    "recommendation", "remarks", "created_at", "updated_at"
]

_HISTORY_COLUMNS = [
    "history_id", "verification_id", "task_id", "event_type",
    "changed_by", "changed_time", "remarks", "gps_lat", "gps_lon",
    "photo", "previous_status", "new_status"
]

class VerificationRepository:
    def _conn(self):
        return sqlite3.connect(DB_PATH)
    
    def _row_to_verif(self, row, cursor) -> Verification:
        cols = [d[0] for d in cursor.description]
        data = dict(zip(cols, row))
        import inspect
        valid_fields = set(inspect.signature(Verification.__init__).parameters.keys()) - {'self'}
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return Verification(**filtered)

    def save(self, verif: Verification, conn: Optional[sqlite3.Connection] = None) -> None:
        own_conn = conn is None
        if own_conn:
            conn = sqlite3.connect(DB_PATH)
        try:
            now = datetime.datetime.now().isoformat()
            if not verif.created_at:
                verif.created_at = now
            verif.updated_at = now

            placeholders = ",".join(["?" for _ in _VERIF_COLUMNS])
            cols = ",".join(_VERIF_COLUMNS)
            values = tuple(getattr(verif, c, None) for c in _VERIF_COLUMNS)
            
            conn.execute(
                f"INSERT OR REPLACE INTO verifications ({cols}) VALUES ({placeholders})",
                values
            )
            if own_conn:
                conn.commit()
        finally:
            if own_conn:
                conn.close()

    def get_by_id(self, verification_id: str) -> Optional[Verification]:
        conn = self._conn()
        try:
            cursor = conn.execute("SELECT * FROM verifications WHERE verification_id=?", (verification_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_verif(row, cursor)
            return None
        finally:
            conn.close()

    def get_by_task(self, task_id: str) -> Optional[Verification]:
        conn = self._conn()
        try:
            cursor = conn.execute("SELECT * FROM verifications WHERE task_id=? ORDER BY created_at DESC LIMIT 1", (task_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_verif(row, cursor)
            return None
        finally:
            conn.close()
            
    def get_pending(self) -> List[Verification]:
        conn = self._conn()
        try:
            cursor = conn.execute("SELECT * FROM verifications WHERE verification_status IN ('Verification Pending', 'Inspection Scheduled', 'Inspection Started')")
            return [self._row_to_verif(row, cursor) for row in cursor.fetchall()]
        finally:
            conn.close()

    def append_history(
        self,
        verification_id: str,
        task_id: str,
        event_type: str,
        changed_by: str,
        previous_status: Optional[str],
        new_status: str,
        changed_time: Optional[str] = None,
        remarks: Optional[str] = None,
        gps_lat: Optional[float] = None,
        gps_lon: Optional[float] = None,
        photo: Optional[str] = None,
        conn: Optional[sqlite3.Connection] = None
    ) -> str:
        history_id = str(uuid.uuid4())
        now = changed_time or datetime.datetime.now().isoformat()
        own_conn = conn is None
        if own_conn:
            conn = sqlite3.connect(DB_PATH)
        try:
            placeholders = ",".join(["?" for _ in _HISTORY_COLUMNS])
            cols = ",".join(_HISTORY_COLUMNS)
            values = (
                history_id, verification_id, task_id, event_type,
                changed_by, now, remarks, gps_lat, gps_lon,
                photo, previous_status, new_status
            )
            conn.execute(
                f"INSERT INTO verification_history ({cols}) VALUES ({placeholders})",
                values
            )
            if own_conn:
                conn.commit()
            return history_id
        finally:
            if own_conn:
                conn.close()

    def get_history(self, verification_id: str) -> List[Dict[str, Any]]:
        conn = self._conn()
        try:
            cursor = conn.execute("SELECT * FROM verification_history WHERE verification_id=? ORDER BY changed_time ASC", (verification_id,))
            cols = [d[0] for d in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_statistics(self) -> Dict[str, Any]:
        conn = self._conn()
        try:
            stats = {
                "total_verified": 0,
                "total_rejected": 0,
                "average_score": 0.0,
                "average_duration_mins": 0.0
            }
            
            c1 = conn.execute("SELECT COUNT(*) FROM verifications WHERE verification_result='PASS'")
            stats["total_verified"] = c1.fetchone()[0] or 0
            
            c2 = conn.execute("SELECT COUNT(*) FROM verifications WHERE verification_result='FAIL'")
            stats["total_rejected"] = c2.fetchone()[0] or 0
            
            c3 = conn.execute("SELECT AVG(verification_score) FROM verifications WHERE verification_score IS NOT NULL")
            stats["average_score"] = round(c3.fetchone()[0] or 0, 2)
            
            c4 = conn.execute("SELECT AVG(verification_duration) FROM verifications WHERE verification_duration IS NOT NULL")
            stats["average_duration_mins"] = round(c4.fetchone()[0] or 0, 2)
            
            return stats
        finally:
            conn.close()
