import sqlite3
import os
import datetime
import logging
from typing import Optional

logger = logging.getLogger(__name__)
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'local_db.sqlite')

class HazardRegistrySync:
    def sync_on_pass(self, hazard_id: str, verified_by: str, verified_at: str, conn: Optional[sqlite3.Connection] = None) -> None:
        own_conn = conn is None
        if own_conn:
            conn = sqlite3.connect(DB_PATH)
        try:
            conn.execute(
                """
                UPDATE hazards 
                SET maintenance_state = 'Verified', 
                    verified_at = ?, 
                    verification_by = ?,
                    updated_at = ?
                WHERE hazard_id = ?
                """,
                (verified_at, verified_by, datetime.datetime.now().isoformat(), hazard_id)
            )
            if own_conn:
                conn.commit()
            logger.info(f"[VERIFY SYNC] Hazard {hazard_id} marked as Verified in registry.")
        finally:
            if own_conn:
                conn.close()

    def sync_on_fail(self, hazard_id: str, conn: Optional[sqlite3.Connection] = None) -> None:
        own_conn = conn is None
        if own_conn:
            conn = sqlite3.connect(DB_PATH)
        try:
            # When rejected, state rolls back to Repair Started, we don't clear assignment.
            # We don't maintain a verification_status column on hazard in our current schema, 
            # we just roll back maintenance_state.
            conn.execute(
                """
                UPDATE hazards 
                SET maintenance_state = 'Repair Started',
                    updated_at = ?
                WHERE hazard_id = ?
                """,
                (datetime.datetime.now().isoformat(), hazard_id)
            )
            if own_conn:
                conn.commit()
            logger.info(f"[VERIFY SYNC] Hazard {hazard_id} rolled back to Repair Started in registry.")
        finally:
            if own_conn:
                conn.close()
