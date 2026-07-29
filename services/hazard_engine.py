import time
import math
import hashlib
from datetime import datetime
from config import Config
from utils.sqlite_db import get_sqlite_conn
from utils.helpers import filter_by_confidence, haversine, majority_severity

_hazard_cache = {
    "data": None,
    "timestamp": 0
}

def invalidate_cache():
    global _hazard_cache
    _hazard_cache["data"] = None
    _hazard_cache["timestamp"] = 0

def normalize_status(raw_status):
    """Normalize statuses internally. PENDING, ASSIGNED, IN_PROGRESS, FIXED, REJECTED, APPROVED"""
    if not raw_status:
        return "PENDING"
    
    s = str(raw_status).lower().strip()
    if s in ["pending", "pending repair", "pending_repair"]: return "PENDING"
    if s in ["assigned"]: return "ASSIGNED"
    if s in ["in progress", "in_progress"]: return "IN_PROGRESS"
    if s in ["completed", "fixed"]: return "FIXED"
    if s in ["rejected"]: return "REJECTED"
    if s in ["approved"]: return "APPROVED"
    return "PENDING"

def format_status_label(norm_status):
    """Expose original labels to frontend."""
    mapping = {
        "PENDING": "Pending Repair",
        "ASSIGNED": "Assigned",
        "IN_PROGRESS": "In Progress",
        "FIXED": "Fixed",
        "REJECTED": "Rejected",
        "APPROVED": "Approved"
    }
    return mapping.get(norm_status, "Pending Repair")

def calculate_priority_score(severity, confidence, days_waiting, report_count):
    """Calculate priority score: Severity + Confidence + Waiting Days + Report Count"""
    sev_map = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    sev_val = sev_map.get((severity or "").lower(), 1)
    
    return sev_val * 10 + confidence * 10 + min(days_waiting, 30) + (report_count * 2)

def calculate_priority_label(severity, confidence, days_waiting, report_count, status):
    """Determine operational priority level based on rules."""
    if status == "FIXED":
        return "Information"
        
    s = str(severity).lower()
    if s in ("high", "critical") and confidence > 0.9 and days_waiting > 7 and report_count > 1:
        return "Critical"
    elif s in ("high", "critical") and status == "PENDING":
        return "High"
    elif s == "medium" and report_count <= 2:
        return "Medium"
    else:
        return "Medium" if s == "medium" else "Low"

def calculate_escalation(status, days_waiting):
    if status == "PENDING":
        if days_waiting <= 2: return "Pending Repair"
        elif days_waiting <= 7: return "High Priority"
        elif days_waiting <= 14: return "Critical"
        elif days_waiting <= 30: return "Escalated to Supervisor"
        else: return "Emergency Maintenance Required"
    return format_status_label(status)
    
def calculate_risk_score(severity, confidence, report_count):
    """Risk engine: 0-100 based on severity, confidence, and reports."""
    sev_map = {"critical": 50, "high": 40, "medium": 20, "low": 5}
    base = sev_map.get((severity or "").lower(), 5)
    
    # Add confidence (0-20)
    conf_add = (confidence * 20)
    
    # Add report count scaling (max 30)
    rep_add = min(report_count * 5, 30)
    
    return min(100, int(base + conf_add + rep_add))

def generate_marker_id(lat, lon):
    """Stable hash for markers."""
    s = f"{round(float(lat), 4)}_{round(float(lon), 4)}"
    return hashlib.md5(s.encode('utf-8')).hexdigest()[:12]

def get_unified_data():
    global _hazard_cache
    now = time.time()
    
    # Single cache 5 seconds
    if _hazard_cache["data"] is not None and (now - _hazard_cache["timestamp"]) < 5:
        return _hazard_cache["data"]

    from app import supabase
    if not supabase:
        return {"error": "Supabase not connected"}
        
    # --- 1. Settings & Assignments ---
    conf_thresh = Config.DEFAULT_CONFIDENCE_THRESHOLD
    assigns = {}
    
    try:
        conn = get_sqlite_conn()
        cur = conn.cursor()
        cur.execute("SELECT detection_sensitivity FROM app_settings WHERE id = 1")
        row = cur.fetchone()
        if row and row["detection_sensitivity"] is not None:
            conf_thresh = float(row["detection_sensitivity"])
            
        cur.execute("SELECT pothole_id, status FROM assignments")
        assigns = {row["pothole_id"]: row["status"] for row in cur.fetchall()}
    except Exception as e:
        print(f"[!] hazard_engine - SQLite Error: {e}")

    # --- 2. Load AI Potholes & Citizen Reports (One fetch each) ---
    p_columns = "id, latitude, longitude, severity, status, confidence, image_url, created_at, type, source_report_id, last_reported_at"
    u_columns = "id, latitude, longitude, severity, status, confidence, media_url, created_at, type, description"
    
    for attempt in range(2):
        try:
            p_res = supabase.table("potholes").select(p_columns).eq("pothole", True).order("created_at", desc=True).limit(500).execute()
            ai_potholes = p_res.data or []
            
            u_res = supabase.table("user_reports").select(u_columns).eq("status", "approved").order("created_at", desc=True).limit(400).execute()
            user_reports = u_res.data or []
            break
        except Exception as e:
            if attempt == 0:
                print(f"[!] hazard_engine - Supabase Query Error: {e}. Retrying in 0.5s...")
                time.sleep(0.5)
            else:
                print(f"[!] hazard_engine - Supabase Query Error (final attempt): {e}")
                if _hazard_cache["data"] is not None:
                    print("[!] Returning expired hazard cached data as fallback.")
                    return _hazard_cache["data"]
                raise

    # --- 3. Normalize & Merge ---
    unified_raw = []
    
    for p in ai_potholes:
        p_conf = p.get("confidence")
        p_conf = float(p_conf) if p_conf is not None else 0.0
        if p_conf < conf_thresh: continue
        
        # Determine internal status
        s_assign = assigns.get(p["id"])
        norm_stat = normalize_status(s_assign) if s_assign else normalize_status(p.get("status"))
            
        unified_raw.append({
            "id": p["id"],
            "latitude": float(p["latitude"]),
            "longitude": float(p["longitude"]),
            "severity": p.get("severity") or "medium",
            "confidence": p_conf,
            "status": norm_stat,
            "created_at": p.get("created_at"),
            "last_reported_at": p.get("last_reported_at") or p.get("created_at"),
            "image": p.get("image_url", ""),
            "source": "AI",
            "type": p.get("type", "pothole"),
            "description": "AI Detection"
        })
        
    for u in user_reports:
        u_conf = u.get("confidence")
        u_conf = float(u_conf) if u_conf is not None else 0.0
        if u_conf < conf_thresh: continue
        
        # User reports are inherently approved if they reach here, but let's check assignment
        s_assign = assigns.get(u["id"])
        norm_stat = normalize_status(s_assign) if s_assign else "APPROVED"
        
        img = u.get("media_url", "")
        
        unified_raw.append({
            "id": u["id"],
            "latitude": float(u["latitude"]),
            "longitude": float(u["longitude"]),
            "severity": u.get("severity") or "medium",
            "confidence": u_conf,
            "status": norm_stat,
            "created_at": u.get("created_at"),
            "last_reported_at": u.get("created_at"),
            "image": img,
            "source": "Citizen",
            "type": u.get("type", "pothole"),
            "description": u.get("description", "Citizen Report")
        })

    # Sort oldest to newest to aggregate correctly (newest takes precedence in metadata)
    unified_raw.sort(key=lambda x: str(x.get("created_at", "")))

    # --- 4. Grouping & Hashing ---
    grid = {}
    CELL_SIZE = 0.0005 # ~55m
    grouped = []
    
    def get_cell_keys(lat, lon):
        x, y = math.floor(lat / CELL_SIZE), math.floor(lon / CELL_SIZE)
        return [(x+dx, y+dy) for dx in (-1,0,1) for dy in (-1,0,1)]

    for r in unified_raw:
        found = False
        lat, lon = r["latitude"], r["longitude"]
        keys = get_cell_keys(lat, lon)
        
        for k in keys:
            if k in grid:
                for g in grid[k]:
                    if haversine(lat, lon, g["latitude"], g["longitude"]) < 50.0:
                        # Merge logic
                        g["_severity_votes"].append(r["severity"])
                        if r["confidence"] > g["confidence"]:
                            g["confidence"] = r["confidence"]
                            
                        # Update temporal limits
                        if not g["created_at"] or r["created_at"] < g["created_at"]:
                            g["created_at"] = r["created_at"]
                        if not g["last_reported_at"] or r["last_reported_at"] > g["last_reported_at"]:
                            g["last_reported_at"] = r["last_reported_at"]
                            
                        # Images and Reports
                        if r["image"] and r["image"] not in g["images"]:
                            g["images"].append(r["image"])
                            if not g["image"]: g["image"] = r["image"]
                            
                        # If a new report comes in, priority logic means status could revert or inherit
                        # We keep the most actionable status
                        if g["status"] == "FIXED" and r["status"] != "FIXED":
                            g["status"] = r["status"]
                            
                        g["reports"].append(r)
                        g["report_count"] += 1
                        
                        found = True
                        break
            if found: break
            
        if not found:
            # Create new group
            group = {
                "marker_id": generate_marker_id(lat, lon),
                "latitude": lat,
                "longitude": lon,
                "severity": r["severity"],
                "_severity_votes": [r["severity"]],
                "confidence": r["confidence"],
                "status": r["status"],
                "created_at": r["created_at"],
                "last_reported_at": r["last_reported_at"],
                "image": r["image"],
                "images": [r["image"]] if r["image"] else [],
                "reports": [r],
                "report_count": 1,
                "source": r["source"], # Primary source
                "type": r["type"]
            }
            grouped.append(group)
            x, y = math.floor(lat / CELL_SIZE), math.floor(lon / CELL_SIZE)
            grid.setdefault((x, y), []).append(group)

    # --- 5. Compute Engine Metrics ---
    now_dt = datetime.utcnow()
    
    hazards = []
    markers = []
    alerts = []
    navigation = []
    
    stats = {
        "total": 0,
        "today": 0,
        "fixed": 0,
        "pending": 0,
        "in_progress": 0
    }
    
    today_str = now_dt.strftime("%Y-%m-%d")

    for g in grouped:
        # Majority severity
        g["severity"] = majority_severity(g.pop("_severity_votes"))
        
        # Format status
        norm_stat = g["status"]
        g["status"] = format_status_label(norm_stat)
        
        # Calculate Waiting Days
        ts_str = g["last_reported_at"] or g["created_at"] or now_dt.isoformat()
        try:
            if ts_str.endswith('Z'): ts_str = ts_str[:-1]
            ts_str = ts_str.split('+')[0]
            created_dt = datetime.fromisoformat(ts_str)
            days_waiting = max(0, (now_dt - created_dt).days)
        except:
            days_waiting = 0
            
        g["days_waiting"] = days_waiting
        g["priority"] = calculate_priority_label(g["severity"], g["confidence"], days_waiting, g["report_count"], norm_stat)
        g["priority_score"] = calculate_priority_score(g["severity"], g["confidence"], days_waiting, g["report_count"])
        g["escalation"] = calculate_escalation(norm_stat, days_waiting)
        g["risk_score"] = calculate_risk_score(g["severity"], g["confidence"], g["report_count"])
        
        # Add to specialized subsets
        hazards.append(g)
        
        # Stats Aggregation
        if norm_stat != "FIXED":
            stats["total"] += 1
            if str(g["created_at"]).startswith(today_str):
                stats["today"] += 1
                
        if norm_stat == "FIXED": stats["fixed"] += 1
        elif norm_stat == "IN_PROGRESS": stats["in_progress"] += 1
        else: stats["pending"] += 1

        # Markers (Only active)
        if norm_stat != "FIXED":
            markers.append(g)
            navigation.append(g) # Nav avoids active hazards
            
        # Alerts (Sortable by priority)
        if norm_stat != "FIXED":
            alerts.append(g)

    # Sort alerts by priority score descending
    alerts.sort(key=lambda x: x["priority_score"], reverse=True)

    master_dataset = {
        "stats": stats,
        "hazards": hazards,
        "markers": markers,
        "alerts": alerts,
        "navigation": navigation,
        "reports": unified_raw
    }
    
    _hazard_cache["data"] = master_dataset
    _hazard_cache["timestamp"] = now
    
    return master_dataset
