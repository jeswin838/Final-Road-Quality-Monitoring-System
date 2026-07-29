import sqlite3
import json
import os
from typing import List, Optional
from models.worker import Worker

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'local_db.sqlite')

class WorkerRepository:
    def _get_connection(self):
        return sqlite3.connect(DB_PATH)

    def get_all_workers(self) -> List[Worker]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM workers")
        rows = cursor.fetchall()
        conn.close()
        
        workers = []
        for row in rows:
            workers.append(self._row_to_worker(row))
        return workers
        
    def get_worker(self, worker_id: str) -> Optional[Worker]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM workers WHERE worker_id=?", (worker_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return self._row_to_worker(row)
        return None
        
    def save_worker(self, worker: Worker):
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT OR REPLACE INTO workers (
            worker_id, employee_code, name, team, department, designation, phone, email,
            zone, district, skills, is_on_leave, is_online, is_emergency_team, certifications,
            languages, shift, latitude, longitude, active_tasks, completed_tasks, experience_years,
            max_daily_tasks, today_tasks, current_workload, vehicle, equipment, status,
            last_assignment, performance_score, average_completion_time, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            worker.worker_id, worker.employee_code, worker.name, worker.team, worker.department,
            worker.designation, worker.phone, worker.email, worker.zone, worker.district,
            json.dumps(worker.skills), worker.is_on_leave, worker.is_online, worker.is_emergency_team,
            json.dumps(worker.certifications), json.dumps(worker.languages), worker.shift,
            worker.latitude, worker.longitude, worker.active_tasks, worker.completed_tasks,
            worker.experience_years, worker.max_daily_tasks, worker.today_tasks, worker.current_workload,
            worker.vehicle, json.dumps(worker.equipment), worker.status, worker.last_assignment,
            worker.performance_score, worker.average_completion_time, worker.created_at, worker.updated_at
        ))
        conn.commit()
        conn.close()
        
    def _row_to_worker(self, row) -> Worker:
        return Worker(
            worker_id=row[0],
            employee_code=row[1],
            name=row[2],
            team=row[3],
            department=row[4],
            designation=row[5],
            phone=row[6],
            email=row[7],
            zone=row[8],
            district=row[9],
            skills=json.loads(row[10]) if row[10] else [],
            is_on_leave=bool(row[11]),
            is_online=bool(row[12]),
            is_emergency_team=bool(row[13]),
            certifications=json.loads(row[14]) if row[14] else [],
            languages=json.loads(row[15]) if row[15] else [],
            shift=row[16],
            latitude=row[17],
            longitude=row[18],
            active_tasks=row[19],
            completed_tasks=row[20],
            experience_years=row[21],
            max_daily_tasks=row[22],
            today_tasks=row[23],
            current_workload=row[24],
            vehicle=row[25],
            equipment=json.loads(row[26]) if row[26] else [],
            status=row[27],
            last_assignment=row[28],
            performance_score=row[29],
            average_completion_time=row[30],
            created_at=row[31],
            updated_at=row[32]
        )
