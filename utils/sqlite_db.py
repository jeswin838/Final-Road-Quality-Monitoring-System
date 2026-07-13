import sqlite3
import os
import threading

_conn = None
_lock = threading.Lock()

def get_sqlite_conn():
    global _conn
    if _conn is None:
        with _lock:
            if _conn is None:
                db_path = "local_db.sqlite"
                # check_same_thread=False allows sharing across Flask threads safely
                _conn = sqlite3.connect(db_path, check_same_thread=False)
                _conn.row_factory = sqlite3.Row
                try:
                    cur = _conn.cursor()
                    cur.execute("CREATE TABLE IF NOT EXISTS assignments (id INTEGER PRIMARY KEY AUTOINCREMENT, pothole_id INTEGER, worker_name TEXT, status TEXT, notes TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
                    cur.execute("CREATE TABLE IF NOT EXISTS app_settings (id INTEGER PRIMARY KEY, detection_sensitivity FLOAT, alert_threshold INTEGER, map_lat FLOAT, map_lon FLOAT, map_zoom INTEGER, auto_refresh_sec INTEGER)")
                    _conn.commit()
                except Exception as e:
                    print(f"[!] SQLite Init Warning: {e}")
    return _conn
