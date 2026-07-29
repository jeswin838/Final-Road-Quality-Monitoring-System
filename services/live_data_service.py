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

def generate_marker_id(lat, lon):
    import hashlib
    s = f"{round(float(lat), 4)}_{round(float(lon), 4)}"
    return hashlib.md5(s.encode('utf-8')).hexdigest()[:12]

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
    p_columns = "id, latitude, longitude, severity, status, confidence, image_url, created_at, type, source_report_id, last_reported_at"
    u_columns = "id, latitude, longitude, severity, status, confidence, media_url, created_at, type, ai_status"
    
    for attempt in range(2):
        try:
            p_res = supabase.table("potholes").select(p_columns).eq("pothole", True).order("created_at", desc=True).limit(500).execute()
            ai_potholes = p_res.data or []
            
            u_res = supabase.table("user_reports").select(u_columns).eq("status", "approved").order("created_at", desc=True).limit(400).execute()
            user_reports = u_res.data or []
            break
        except Exception as e:
            if attempt == 0:
                print(f"[!] LiveData Service - Supabase Query Error: {e}. Retrying in 0.5s...")
                time.sleep(0.5)
            else:
                print(f"[!] LiveData Service - Supabase Query Error (final attempt): {e}")
                if _cache["data"] is not None:
                    print("[!] Returning expired cached data as fallback.")
                    return _cache["data"]
                raise

    # Map media_url to image_url for user reports to align with downstream logic
    for u in user_reports:
        u["source"] = "Citizen"
        url = u.get("media_url")
        if url and not url.startswith("http") and not url.startswith("/static"):
            url = f"{Config.SUPABASE_URL}/storage/v1/object/public/pothole-images/{url}"
        u["media_url"] = url
        u["image_url"] = url

    for p in ai_potholes:
        p["source"] = "AI"
        url = p.get("image_url")
        if url and not url.startswith("http") and not url.startswith("/static"):
            p["image_url"] = f"{Config.SUPABASE_URL}/storage/v1/object/public/pothole-images/{url}"

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
        # Normalize status
        if s_assign == "Pending": s_assign = "Pending Repair"
        elif s_assign == "Completed": s_assign = "Fixed"

        if s_assign == "Fixed":
            fixed += 1
        elif s_assign == "In Progress":
            inprog += 1
        else:
            pending += 1

        raw_status = str(p.get("status") or "approved").lower()
        
        # Enriched dict for lists
        enriched_p = dict(p)
        enriched_p["status"] = s_assign
        
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
                                
                        # Avoid duplicates by image filename, preferring Citizen reports
                        is_dup = False
                        p_img = p.get("image_url")
                        img_name = p_img.strip().split('/')[-1] if p_img else None
                        
                        if img_name:
                            for r in g.get("reports", []):
                                r_img = r.get("image_url") or r.get("media_url")
                                r_img_name = r_img.strip().split('/')[-1] if r_img else None
                                if r_img_name == img_name:
                                    if p.get("source") == "Citizen" and r.get("source") != "Citizen":
                                        # Prefer the Citizen copy which has more metadata (description etc.)
                                        g["reports"].remove(r)
                                        g["reports"].append(p)
                                    is_dup = True
                                    break
                                    
                        if not is_dup:
                            if "reports" not in g:
                                g["reports"] = []
                            g["reports"].append(p)
                                
                        found = True
                        break
            if found:
                break
                
        if not found:
            p_ts = p.get("last_reported_at") or p.get("created_at")
            p_url = p.get("image_url", "")
            p_source = p.get("source", "AI")
            p_sev = (p.get("severity") or "").lower() or None
            
            # Resolve status for this group anchor correctly
            p_assign = assigns.get(p["id"], "Pending")
            if p_assign == "Pending": p_assign = "Pending Repair"
            elif p_assign == "Completed": p_assign = "Fixed"
            
            group_type = "user_report" if p_source == "Citizen" else p.get("type", "pothole")
            
            group = {
                "marker_id": generate_marker_id(lat, lon),
                "id": p.get("id"),
                "latitude": lat,
                "longitude": lon,
                "severity": p_sev,
                "_severity_votes": [p_sev] if p_sev else [],
                "report_count": p.get("report_count") or 1,
                "created_at": p.get("created_at"),
                "last_reported_at": p_ts,
                "status": p_assign,
                "image": p_url,
                "all_images": [p_url] if p_url else [],
                "reports": [p],
                "source": p_source,
                "type": group_type,
                "description": p.get("type", "Pothole detected by AI"),
                "confidence": p.get("confidence") or 0.0,
            }
            final_groups.append(group)
            
            x, y = math.floor(lat / CELL_SIZE), math.floor(lon / CELL_SIZE)
            grid.setdefault((x, y), []).append(group)

    # Resolve severity votes and calculate operational metrics
    now_dt = datetime.utcnow()
    for g in final_groups:
        if g.get("_severity_votes"):
            g["severity"] = majority_severity(g.get("_severity_votes", []))
        if "_severity_votes" in g:
            del g["_severity_votes"]
            
        # 1. Calculate wait time
        ts_str = g.get("last_reported_at") or g.get("created_at") or now_dt.isoformat()
        try:
            if ts_str.endswith('Z'): ts_str = ts_str[:-1]
            created_dt = datetime.fromisoformat(ts_str.split('+')[0])
            days_waiting = (now_dt - created_dt).days
        except:
            days_waiting = 0
        g["days_waiting"] = max(0, days_waiting)
        
        # 2. Priority Logic
        s = str(g.get("severity", "low")).lower()
        conf = float(g.get("confidence", 0))
        reps = int(g.get("report_count", 1))
        stat = str(g.get("status", "")).lower()
        
        if stat == "fixed":
            g["priority"] = "Information"
        elif s in ("high", "critical") and conf > 0.9 and days_waiting > 7:
            g["priority"] = "Critical"
        elif s in ("high", "critical") and stat == "pending repair":
            g["priority"] = "High"
        elif s == "medium" or reps > 2:
            g["priority"] = "Medium"
        else:
            g["priority"] = "Low"
            
        # 3. Escalation Logic
        if stat == "pending repair":
            if days_waiting <= 2: g["escalation"] = "Pending Repair"
            elif days_waiting <= 7: g["escalation"] = "High Priority"
            elif days_waiting <= 14: g["escalation"] = "Critical"
            elif days_waiting <= 30: g["escalation"] = "Escalated to Supervisor"
            else: g["escalation"] = "Emergency Maintenance Required"
        else:
            g["escalation"] = g.get("status")
        
    alerts = [g for g in final_groups] # Send all for operations center
    map_groups = [g for g in final_groups if str(g.get("status", "")).lower() != "fixed"]

    payload = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "stats": stats,
        "alerts": alerts,
        "map": map_groups,
        "approved": approved_list,
        "pending": pending_list
    }

    _cache["data"] = payload
    _cache["timestamp"] = now

    return payload
