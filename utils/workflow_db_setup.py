import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'local_db.sqlite')


def setup_workflow_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # ── maintenance_tasks (recreate with all columns) ──────────────────────────
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS maintenance_tasks (
        task_id                 TEXT PRIMARY KEY,
        hazard_id               TEXT NOT NULL,
        assignment_id           TEXT,
        maintenance_task_id     TEXT,
        current_state           TEXT NOT NULL,
        workflow_version        TEXT,
        row_version             INTEGER DEFAULT 1,
        reopen_count            INTEGER DEFAULT 0,
        last_reopened_at        TEXT,
        created_time            TEXT,
        updated_time            TEXT,
        created_by              TEXT,
        last_modified_by        TEXT,
        closed_time             TEXT,
        assigned_at             TEXT,
        accepted_at             TEXT,
        travel_started_at       TEXT,
        arrived_at              TEXT,
        inspection_started_at   TEXT,
        repair_started_at       TEXT,
        temporary_completed_at  TEXT,
        repair_completed_at     TEXT,
        verification_started_at TEXT,
        verified_at             TEXT,
        closed_at               TEXT
    )
    ''')

    # ── maintenance_history (UUID primary key, hash chain, enriched audit) ─────
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS maintenance_history (
        history_id          TEXT PRIMARY KEY,
        task_id             TEXT NOT NULL,
        previous_state      TEXT,
        new_state           TEXT NOT NULL,
        changed_by          TEXT,
        actor_type          TEXT,
        changed_time        TEXT NOT NULL,
        remarks             TEXT,
        gps_lat             REAL,
        gps_lon             REAL,
        gps_accuracy        REAL,
        photo_before        TEXT,
        photo_after         TEXT,
        verification_photo  TEXT,
        device              TEXT,
        device_type         TEXT,
        previous_hash       TEXT,
        current_hash        TEXT
    )
    ''')

    # ── workflow_events (enriched with source/version) ─────────────────────────
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS workflow_events (
        event_id        TEXT PRIMARY KEY,
        task_id         TEXT NOT NULL,
        event_type      TEXT NOT NULL,
        event_source    TEXT,
        event_version   TEXT,
        event_time      TEXT NOT NULL,
        payload         TEXT
    )
    ''')

    conn.commit()
    conn.close()
    print("[WORKFLOW] Database setup complete.")


def migrate_workflow_db():
    """Safe ALTER TABLE migration for existing databases."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    def add_column_if_missing(table, column, col_type, default=None):
        cursor.execute(f"PRAGMA table_info({table})")
        cols = [row[1] for row in cursor.fetchall()]
        if column not in cols:
            defval = f" DEFAULT {default}" if default is not None else ""
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}{defval}")
            print(f"[MIGRATE] Added {table}.{column}")

    # maintenance_tasks
    add_column_if_missing("maintenance_tasks", "row_version",         "INTEGER", 1)
    add_column_if_missing("maintenance_tasks", "reopen_count",        "INTEGER", 0)
    add_column_if_missing("maintenance_tasks", "last_reopened_at",    "TEXT")
    add_column_if_missing("maintenance_tasks", "maintenance_task_id", "TEXT")

    # maintenance_history
    add_column_if_missing("maintenance_history", "actor_type",      "TEXT")
    add_column_if_missing("maintenance_history", "device_type",     "TEXT")
    add_column_if_missing("maintenance_history", "gps_accuracy",    "REAL")
    add_column_if_missing("maintenance_history", "previous_hash",   "TEXT")
    add_column_if_missing("maintenance_history", "current_hash",    "TEXT")

    # workflow_events
    add_column_if_missing("workflow_events", "event_source",   "TEXT")
    add_column_if_missing("workflow_events", "event_version",  "TEXT")

    conn.commit()
    conn.close()
    print("[WORKFLOW] Migration complete.")


if __name__ == "__main__":
    setup_workflow_db()
    migrate_workflow_db()
