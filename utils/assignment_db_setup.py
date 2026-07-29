import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'local_db.sqlite')

def setup_assignment_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Drop existing tables
    cursor.execute('DROP TABLE IF EXISTS workers')
    cursor.execute('DROP TABLE IF EXISTS assignments')
    cursor.execute('DROP TABLE IF EXISTS assignment_history')
    cursor.execute('DROP TABLE IF EXISTS worker_skills')
    
    # 1. workers
    cursor.execute('''
    CREATE TABLE workers (
        worker_id TEXT PRIMARY KEY,
        employee_code TEXT,
        name TEXT,
        team TEXT,
        department TEXT,
        designation TEXT,
        phone TEXT,
        email TEXT,
        zone TEXT,
        district TEXT,
        skills TEXT, -- JSON array
        is_on_leave BOOLEAN,
        is_online BOOLEAN,
        is_emergency_team BOOLEAN,
        certifications TEXT, -- JSON array
        languages TEXT, -- JSON array
        shift TEXT,
        latitude REAL,
        longitude REAL,
        active_tasks INTEGER DEFAULT 0,
        completed_tasks INTEGER DEFAULT 0,
        experience_years INTEGER,
        max_daily_tasks INTEGER DEFAULT 5,
        today_tasks INTEGER DEFAULT 0,
        current_workload INTEGER DEFAULT 0,
        vehicle TEXT,
        equipment TEXT, -- JSON array
        status TEXT,
        last_assignment TEXT,
        performance_score REAL,
        average_completion_time REAL,
        created_at TEXT,
        updated_at TEXT
    )
    ''')
    
    # 3. assignments
    cursor.execute('''
    CREATE TABLE assignments (
        assignment_id TEXT PRIMARY KEY,
        hazard_id TEXT,
        worker_id TEXT,
        recommended_team TEXT,
        recommended_vehicle TEXT,
        recommended_equipment TEXT, -- JSON array
        recommended_eta REAL,
        recommended_distance REAL,
        recommendation_score REAL,
        score_breakdown TEXT, -- JSON
        recommendation_reason TEXT,
        approved_by_admin BOOLEAN DEFAULT 0,
        assigned_time TEXT,
        accepted_at TEXT,
        travel_start TEXT,
        repair_start TEXT,
        repair_completed TEXT,
        verification_completed TEXT,
        status TEXT,
        estimated_completion TEXT,
        priority TEXT,
        history TEXT -- JSON array
    )
    ''')
    
    # 4. assignment_history (append only)
    cursor.execute('''
    CREATE TABLE assignment_history (
        history_id INTEGER PRIMARY KEY AUTOINCREMENT,
        assignment_id TEXT,
        status TEXT,
        changed_at TEXT,
        changed_by TEXT,
        notes TEXT
    )
    ''')
    
    conn.commit()
    conn.close()
    print("Database setup complete.")

if __name__ == "__main__":
    setup_assignment_db()
