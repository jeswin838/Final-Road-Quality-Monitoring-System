import sqlite3
import json
import os
from typing import List, Optional
from models.assignment import Assignment
from models.assignment_history import AssignmentHistory

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'local_db.sqlite')

class AssignmentRepository:
    def _get_connection(self):
        return sqlite3.connect(DB_PATH)

    def save_assignment(self, assignment: Assignment):
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT OR REPLACE INTO assignments (
            assignment_id, hazard_id, worker_id, recommended_team, recommended_vehicle,
            recommended_equipment, recommended_eta, recommended_distance, recommendation_score,
            score_breakdown, recommendation_reason, approved_by_admin, assigned_time, accepted_at, travel_start, repair_start,
            repair_completed, verification_completed, status, estimated_completion, priority, history
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            assignment.assignment_id, assignment.hazard_id, assignment.worker_id,
            assignment.recommended_team, assignment.recommended_vehicle, json.dumps(assignment.recommended_equipment),
            assignment.recommended_eta, assignment.recommended_distance, assignment.recommendation_score,
            json.dumps(assignment.score_breakdown), assignment.recommendation_reason,
            assignment.approved_by_admin,
            assignment.assigned_time, assignment.accepted_at, assignment.travel_start,
            assignment.repair_start, assignment.repair_completed, assignment.verification_completed,
            assignment.status, assignment.estimated_completion, assignment.priority,
            json.dumps(assignment.history)
        ))
        conn.commit()
        conn.close()

    def get_assignment(self, assignment_id: str) -> Optional[Assignment]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM assignments WHERE assignment_id=?", (assignment_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return self._row_to_assignment(row)
        return None

    def get_assignment_by_hazard(self, hazard_id: str) -> Optional[Assignment]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM assignments WHERE hazard_id=?", (hazard_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return self._row_to_assignment(row)
        return None
        
    def get_all_assignments(self) -> List[Assignment]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM assignments")
        rows = cursor.fetchall()
        conn.close()
        return [self._row_to_assignment(r) for r in rows]

    def _row_to_assignment(self, row) -> Assignment:
        return Assignment(
            assignment_id=row[0],
            hazard_id=row[1],
            worker_id=row[2],
            recommended_team=row[3],
            recommended_vehicle=row[4],
            recommended_equipment=json.loads(row[5]) if row[5] else [],
            recommended_eta=row[6],
            recommended_distance=row[7],
            recommendation_score=row[8],
            score_breakdown=json.loads(row[9]) if row[9] else {},
            recommendation_reason=row[10],
            approved_by_admin=bool(row[11]),
            assigned_time=row[12],
            accepted_at=row[13],
            travel_start=row[14],
            repair_start=row[15],
            repair_completed=row[16],
            verification_completed=row[17],
            status=row[18],
            estimated_completion=row[19],
            priority=row[20],
            history=json.loads(row[21]) if row[21] else []
        )

    def append_history(self, assignment_id: str, status: str, changed_at: str, changed_by: str, notes: str):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO assignment_history (assignment_id, status, changed_at, changed_by, notes)
        VALUES (?, ?, ?, ?, ?)
        ''', (assignment_id, status, changed_at, changed_by, notes))
        conn.commit()
        conn.close()
        
    def get_history(self, assignment_id: str) -> List[AssignmentHistory]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM assignment_history WHERE assignment_id=? ORDER BY history_id ASC", (assignment_id,))
        rows = cursor.fetchall()
        conn.close()
        return [AssignmentHistory(history_id=r[0], assignment_id=r[1], status=r[2], changed_at=r[3], changed_by=r[4], notes=r[5]) for r in rows]
