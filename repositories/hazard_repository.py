import logging
from typing import List, Dict, Any
from utils.retry import retry_supabase, retry_sqlite
from utils.sqlite_db import get_sqlite_conn

logger = logging.getLogger("HazardRepository")
logger.setLevel(logging.INFO)
if not logger.handlers:
    ch = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

def fetch_raw_ai_potholes() -> List[Dict[str, Any]]:
    """Retrieve raw AI potholes from Supabase using retry helper."""
    from app import supabase
    if not supabase:
        logger.warning("Supabase client is not connected.")
        return []
        
    p_columns = "id, latitude, longitude, severity, status, confidence, image_url, created_at, type, source_report_id, last_reported_at"
    
    def _query():
        p_res = supabase.table("potholes").select(p_columns).eq("pothole", True).order("created_at", desc=True).limit(500).execute()
        return p_res.data or []
        
    return retry_supabase(_query)

def fetch_raw_citizen_reports() -> List[Dict[str, Any]]:
    """Retrieve raw Citizen reports from Supabase using retry helper."""
    from app import supabase
    if not supabase:
        logger.warning("Supabase client is not connected.")
        return []
        
    u_columns = "id, latitude, longitude, severity, status, confidence, media_url, created_at, type, ai_status"
    
    def _query():
        u_res = supabase.table("user_reports").select(u_columns).eq("status", "approved").order("created_at", desc=True).limit(400).execute()
        return u_res.data or []
        
    return retry_supabase(_query)

def fetch_sqlite_assignments() -> List[Dict[str, Any]]:
    """Retrieve SQLite assignments using retry helper."""
    def _query():
        conn = get_sqlite_conn()
        cur = conn.cursor()
        try:
            cur.execute("SELECT hazard_id, worker_id as worker_name, status, recommendation_reason as notes, assigned_time as created_at FROM assignments")
            return [dict(row) for row in cur.fetchall()]
        except Exception:
            # Legacy DB fallback
            cur.execute("SELECT pothole_id, worker_name, status FROM assignments")
            return [dict(row) for row in cur.fetchall()]
            
    try:
        return retry_sqlite(_query)
    except Exception as e:
        logger.warning(f"Failed to fetch SQLite assignments: {e}")
        return []

def fetch_sqlite_settings() -> Dict[str, Any]:
    """Retrieve SQLite settings sensitivity using retry helper."""
    def _query():
        conn = get_sqlite_conn()
        cur = conn.cursor()
        cur.execute("SELECT detection_sensitivity FROM app_settings WHERE id = 1")
        row = cur.fetchone()
        return dict(row) if row else {}
        
    try:
        return retry_sqlite(_query)
    except Exception as e:
        logger.warning(f"Failed to fetch SQLite settings: {e}")
        return {}
