import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'local_db.sqlite')

def setup_verification_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # ── verifications ──────────────────────────────────────────────────────────
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS verifications (
        verification_id         TEXT PRIMARY KEY,
        task_id                 TEXT NOT NULL,
        hazard_id               TEXT NOT NULL,
        assignment_id           TEXT,
        verified_by             TEXT,
        engineer_name           TEXT,
        engineer_department     TEXT,
        verification_status     TEXT NOT NULL,
        verification_result     TEXT,
        verification_reason     TEXT,
        verification_notes      TEXT,
        before_photo            TEXT,
        after_photo             TEXT,
        verification_photo      TEXT,
        gps_lat                 REAL,
        gps_lon                 REAL,
        gps_accuracy            REAL,
        verified_time           TEXT,
        verification_duration   REAL,
        verification_score      INTEGER,
        verification_grade      TEXT,
        recommendation          TEXT,
        remarks                 TEXT,
        created_at              TEXT,
        updated_at              TEXT
    )
    ''')

    # ── verification_history (append-only) ─────────────────────────────────────
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS verification_history (
        history_id              TEXT PRIMARY KEY,
        verification_id         TEXT NOT NULL,
        task_id                 TEXT NOT NULL,
        event_type              TEXT NOT NULL,
        changed_by              TEXT,
        changed_time            TEXT NOT NULL,
        remarks                 TEXT,
        gps_lat                 REAL,
        gps_lon                 REAL,
        photo                   TEXT,
        previous_status         TEXT,
        new_status              TEXT NOT NULL
    )
    ''')

    conn.commit()
    conn.close()
    print("[VERIFY] Database setup complete.")

if __name__ == "__main__":
    setup_verification_db()
