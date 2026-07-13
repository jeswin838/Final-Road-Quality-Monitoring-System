import time
import math
from datetime import datetime
from config import Config
from utils.sqlite_db import get_sqlite_conn
from utils.helpers import filter_by_confidence, haversine, majority_severity

_cache = {
    "data": None,
    "timestamp": 0
}

def get_all_data():
    now = time.time()
    if _cache["data"] is not None and (now - _cache["timestamp"]) < 3:
        return _cache["data"]

    from app import supabase
    if not supabase:
        return {"error": "Supabase not connected"}

    # 1. Fetch global settings
    conf_thresh = Config.DEFAULT_CONFIDENCE_THRESHOLD
    try:
        conn = get_sqlite_conn()
        cur = conn.cursor()
        cur.execute("SELECT detection_sensitivity FROM app_settings WHERE id = 1")
        row = cur.fetchone()
        if row and row["detection_sensitivity"] is not None:
            conf_thresh = float(row["detection_sensitivity"])
    except Exception as e:
        print(f"[!] LiveData Service - SQLite Settings Error: {e}")

    # 2. Fetch assignments
    try:
        conn = get_sqlite_conn()
        cur = conn.cursor()
        cur.execute("SELECT pothole_id, status FROM assignments")
        assigns = {row["pothole_id"]: row["status"] for row in cur.fetchall()}
    except Exception as e:
        print(f"[!] LiveData Service - SQLite Assignments Error: {e}")
        assigns = {}

    # 3. Single Supabase queries with column projection
    columns = "id, latitude, longitude, severity, status, confidence, image_url, created_at, type, ai_status, source_report_id, last_reported_at"
    
    p_res = supabase.table("potholes").select(columns).eq("pothole", True).order("created_at", desc=True).limit(500).execute()
    ai_potholes = p_res.data or []
    
    u_res = supabase.table("user_reports").select(columns).eq("status", "approved").order("created_at", desc=True).limit(400).execute()
    user_reports = u_res.data or []

    # 4. Filter by confidence
    ai_potholes = filter_by_confidence(ai_potholes, conf_thresh)
    user_reports = filter_by_confidence(user_reports, conf_thresh)
    user_reports = [u for u in user_reports if str(u.get("status", "")).lower() == "approved"]

    # 5. Build Stats (from raw AI potholes)
    total = len(ai_potholes)
    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    today = sum(1 for p in ai_potholes if str(p.get("created_at", "")).startswith(today_str))
    
    fixed, pending, inprog = 0, 0, 0
    approved_list = []
    pending_list = []

    for p in ai_potholes:
        s_assign = assigns.get(p["id"], "Pending")
        if s_assign in ("Completed", "Fixed"):
            fixed += 1
        elif s_assign == "In Progress":
            inprog += 1
        else:
            pending += 1

        raw_status = str(p.get("status") or "approved").lower()
        
        # Enriched dict for lists
        enriched_p = dict(p)
        enriched_p["status"] = assigns.get(p["id"], p.get("status") or "Pending")
        
        if raw_status == "approved":
            approved_list.append(enriched_p)
        elif raw_status == "pending":
            pending_list.append(enriched_p)

    stats = {
        "total": total,
        "today": today,
        "fixed": fixed,
        "pending": pending,
        "in_progress": inprog
    }

    # 6. Spatial Hash Map Grouping for Map & Alerts (O(N) time complexity)
    grid = {}
    CELL_SIZE = 0.0005 # Approx 55 meters
    final_groups = []

    def get_cell_keys(lat, lon):
        x, y = math.floor(lat / CELL_SIZE), math.floor(lon / CELL_SIZE)
        return [(x+dx, y+dy) for dx in (-1,0,1) for dy in (-1,0,1)]

    # Combine AI and User Reports for mapping
    # Only approved ones should show on map/alerts usually, but let's follow the old unified logic
    map_sources = [p for p in ai_potholes if str(p.get("status") or "").lower() == "approved"] + user_reports
    
    # Sort so newest handles group anchoring
    map_sources.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    for p in map_sources:
        try:
            lat, lon = float(p["latitude"]), float(p["longitude"])
        except:
            continue
            
        found = False
        keys = get_cell_keys(lat, lon)
        
        for k in keys:
            if k in grid:
                for g in grid[k]:
                    if haversine(lat, lon, g["latitude"], g["longitude"]) < 50.0:
                        p_sev = (p.get("severity") or "medium").lower()
                        g["_severity_votes"].append(p_sev)
                        g["report_count"] += 1
                        p_ts = p.get("last_reported_at") or p.get("created_at")
                        if p_ts and (not g["last_reported_at"] or p_ts > g["last_reported_at"]):
                            g["last_reported_at"] = p_ts
                            
                        # Add image to collection if present
                        p_img = p.get("image_url")
                        if p_img and p_img not in g["all_images"]:
                            g["all_images"].append(p_img)
                            if not g["image"]:
                                g["image"] = p_img
                                
                        found = True
                        break
            if found:
                break
                
        if not found:
            p_ts = p.get("last_reported_at") or p.get("created_at")
            p_url = p.get("image_url", "")
            p_source = "Citizen" if (p_url and "user_report" in p_url) else "AI"
            p_sev = (p.get("severity") or "").lower() or None
            
            group = {
                "id": p.get("id"),
                "latitude": lat,
                "longitude": lon,
                "severity": p_sev,
                "_severity_votes": [p_sev] if p_sev else [],
                "report_count": p.get("report_count") or 1,
                "last_reported_at": p_ts,
                "status": assigns.get(p.get("id"), p.get("status") or "Pending"),
                "image": p_url,
                "all_images": [p_url] if p_url else [],
                "source": p_source,
                "type": p.get("type", "pothole"),
                "description": p.get("type", "Pothole detected by AI"),
                "confidence": p.get("confidence") or 0.0,
            }
            final_groups.append(group)
            
            x, y = math.floor(lat / CELL_SIZE), math.floor(lon / CELL_SIZE)
            grid.setdefault((x, y), []).append(group)

    # Resolve severity votes
    for g in final_groups:
        if g["_severity_votes"]:
            g["severity"] = majority_severity(g["_severity_votes"])
        del g["_severity_votes"]
        
    alerts = [g for g in final_groups if str(g.get("severity")).lower() in ["high", "critical"]]

    payload = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "stats": stats,
        "alerts": alerts,
        "map": final_groups,
        "approved": approved_list,
        "pending": pending_list
    }

    _cache["data"] = payload
    _cache["timestamp"] = now

    return payload
