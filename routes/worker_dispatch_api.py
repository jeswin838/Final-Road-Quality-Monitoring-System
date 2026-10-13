import math
import sqlite3
import datetime
import traceback
import time
from functools import wraps
from flask import Blueprint, request, jsonify, session
from routes.api import get_sqlite, get_supabase, Config
from utils.helpers import haversine

worker_dispatch_api = Blueprint("worker_dispatch_api", __name__, url_prefix="/api/worker")

class LoggingCursor:
    def __init__(self, cursor, log_list):
        self.cursor = cursor
        self.log_list = log_list
    def execute(self, sql, params=None):
        self.log_list.append({"sql": sql, "params": params})
        if params:
            return self.cursor.execute(sql, params)
        return self.cursor.execute(sql)
    def fetchone(self): return self.cursor.fetchone()
    def fetchall(self): return self.cursor.fetchall()
    @property
    def rowcount(self): return self.cursor.rowcount

def worker_api(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        start_time = time.time()
        worker_id = session.get("user_id")
        log_data = {
            "worker_id": worker_id,
            "endpoint": request.path,
            "sql_executed": [],
            "records_returned": 0,
            "error": None
        }
        
        # Inject log_list into kwargs so the route can log SQL
        kwargs["sql_log"] = log_data["sql_executed"]
        
        try:
            if "user_id" not in session or session.get("role") != "worker":
                return jsonify({"success": False, "message": "Unauthorized"}), 403
                
            res = f(*args, **kwargs)
            
            # If endpoint returns a Flask Response (from jsonify), unpack it
            # But wait, to wrap in success: true, the endpoint should return raw dict/list
            if isinstance(res, tuple):
                data, status = res
            else:
                data, status = res, 200
                
            if isinstance(data, dict) and "success" in data:
                final_res = data
            else:
                final_res = {"success": True, "data": data}
                
            if isinstance(data, list):
                log_data["records_returned"] = len(data)
            elif isinstance(data, dict):
                log_data["records_returned"] = 1
                
            return jsonify(final_res), status
            
        except Exception as e:
            err_trace = traceback.format_exc()
            log_data["error"] = err_trace
            print(f"WORKER API ERROR 500: {err_trace}")
            return jsonify({
                "success": False,
                "error": str(e),
                "message": "Internal Server Error"
            }), 500
        finally:
            exec_time = time.time() - start_time
            print(f"[WORKER API LOG] Worker: {log_data['worker_id']} | End: {log_data['endpoint']} | Time: {exec_time:.3f}s | Recs: {log_data['records_returned']} | Err: {'Yes' if log_data['error'] else 'No'}")
            if log_data["sql_executed"]:
                print(f"[WORKER API LOG SQL] {log_data['sql_executed']}")
                
    return decorated


def _get_active_assignment(worker_id, sql_log):
    from routes.api import get_supabase
    supabase = get_supabase()
    
    # Query Supabase for active assignments
    res = supabase.table("assignments").select("*") \
        .eq("worker_id", worker_id) \
        .in_("status", ['Assigned', 'Accepted', 'Travelling', 'Reached Site', 'Before Photo Verified', 'Repair Started', 'Repair Completed', 'After Photo Verified']) \
        .order("id", desc=True) \
        .limit(1).execute()
        
    sql_log.append({"sql": "Supabase assignments query", "params": {"worker_id": worker_id}})
    
    if res.data and len(res.data) > 0:
        row = res.data[0]
        print(f"[DEBUG] Active Assignment Found for Worker {worker_id}: ID={row['hazard_id']} Status={row['status']}")
        return row
    else:
        print(f"[DEBUG] No Active Assignment found for Worker {worker_id}")
        return None

def safe_float(value, default=0.0):
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default

def safe_int(value, default=0):
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default

def _get_hazard_details(hazard_id, hazard_source=None):
    from services.hazard_registry import registry_cache
    import datetime
    
    master_id = str(hazard_id)
    if not (master_id.startswith("AI-") or master_id.startswith("USER-")):
        source_prefix = "USER-" if hazard_source == "user_reports" or hazard_source == "USER" else "AI-"
        master_id = f"{source_prefix}{hazard_id}"
        
    cached_hazard = registry_cache.get(master_id)
    
    if cached_hazard:
        h_dict = cached_hazard._cached_dict
        
        wait = "Unknown"
        first_rep = h_dict.get("first_reported_at") or h_dict.get("created_at")
        if first_rep:
            try:
                dt = datetime.datetime.fromisoformat(first_rep.replace("Z", "+00:00"))
                delta = datetime.datetime.now(datetime.timezone.utc) - dt
                days = delta.days
                if days > 0: wait = f"{days} days"
                else: wait = f"{delta.seconds // 3600} hours"
            except: pass
            
        return {
            "id": h_dict.get("hazard_id"),
            "image": h_dict.get("image"),
            "latitude": h_dict.get("latitude", 0.0),
            "longitude": h_dict.get("longitude", 0.0),
            "severity": h_dict.get("severity", "Medium"),
            "confidence": h_dict.get("confidence", 0.0),
            "created_at": h_dict.get("created_at"),
            "first_reported_at": first_rep,
            "waiting_time": wait,
            "reports_count": h_dict.get("report_count", 1),
            "risk_score": h_dict.get("priority_breakdown", {}).get("risk_score", 50)
        }
        
    # Fallback to database if not in cache
    try:
        numeric_id = int(str(hazard_id).replace('AI-', '').replace('USER-', ''))
    except ValueError:
        return None
        
    supabase = get_supabase()
    try:
        res = supabase.table("potholes").select("*").eq("id", numeric_id).execute()
        data = res.data
        
        if not data:
            res = supabase.table("user_reports").select("*").eq("id", numeric_id).execute()
            data = res.data
    except Exception as e:
        print(f"[!] Supabase error in _get_hazard_details for ID {hazard_id}: {e}")
        return None
        
    if data:
        p = data[0]
        wait = "Unknown"
        if p.get("created_at"):
            try:
                dt = datetime.datetime.fromisoformat(p["created_at"].replace("Z", "+00:00"))
                delta = datetime.datetime.now(datetime.timezone.utc) - dt
                days = delta.days
                if days > 0: wait = f"{days} days"
                else: wait = f"{delta.seconds // 3600} hours"
            except: pass
        
        url = p.get("image_url") or p.get("media_url")
        if url and not url.startswith("http") and not url.startswith("/static"):
            from config import Config
            url = f"{Config.SUPABASE_URL.rstrip('/')}/storage/v1/object/public/pothole-images/{url}"
            
        p_lat = safe_float(p.get("latitude"), 0.0)
        p_lon = safe_float(p.get("longitude"), 0.0)
            
        return {
            "id": p["id"],
            "image": url,
            "latitude": p_lat,
            "longitude": p_lon,
            "severity": p.get("severity") or "Medium",
            "confidence": safe_float(p.get("confidence"), 0.0),
            "created_at": p.get("created_at"),
            "waiting_time": wait,
            "reports_count": safe_int(p.get("reports_count"), 1),
            "risk_score": p.get("risk_score", 50)
        }
    return None

@worker_dispatch_api.route("/available-jobs", methods=["GET"])
@worker_api
def get_available_jobs(sql_log):
    # Live GPS calculations are now strictly handled by the frontend browser
    from services.hazard_registry import registry_cache
    from routes.api import get_supabase
    
    worker_id = session.get("user_id")
    supabase = get_supabase()
    
    print(f"\n[WORKER JOBS] Fetching available jobs for worker: {worker_id}")
    
    # Query Supabase for relevant assignments
    # status='Assigned' AND worker_id=worker_id OR status='Available' AND worker_id IS NULL
    # PostgREST allows or syntax: or=(and(status.eq.Assigned,worker_id.eq.X),and(status.eq.Available,worker_id.is.null))
    res = supabase.table("assignments").select("*") \
        .or_(f"and(status.eq.Assigned,worker_id.eq.{worker_id}),and(status.eq.Needs Rework,worker_id.eq.{worker_id}),and(status.eq.Available,worker_id.is.null)") \
        .execute()
        
    sql_log.append({"sql": "Supabase assignments OR query", "params": {"worker_id": worker_id}})
    assignments = res.data if res.data else []
    
    print(f"[WORKER JOBS] Assignments fetched from database: {len(assignments)}")
    
    import time
    import traceback
    start_time = time.time()
    
    jobs = []
    seen_images = set()
    skipped_count = 0
    processed_count = 0
    
    with registry_cache.lock:
        hazard_dict = registry_cache.data
        
    for a in assignments:
        try:
            print("==============================")
            print("Processing Assignment")
            assignment_id = a.get("id")
            print(f"Assignment ID: {assignment_id}")
            hid_str = str(a.get("hazard_id"))
            print(f"Hazard ID: {hid_str}")
            raw_source = a.get("hazard_source")
            
            # Normalize hazard_source to handle variations like 'ai_detections' and 'user_reports'
            # Ensures consistent master_id generation (AI-123 or USER-123)
            h_source_normalized = "USER" if raw_source in ("USER", "user_reports") else "AI"
            
            master_id = f"{h_source_normalized}-{hid_str}"
            
            # Primary lookup in registry_cache
            h = hazard_dict.get(master_id)
            if not h:
                h = hazard_dict.get(hid_str) # Legacy check
                
            is_fallback = False
            hazard_data = None
            
            if h:
                print(f"Registry HIT/MISS: HIT for key {master_id}")
                # Map object attributes to a dict format for processing
                hazard_data = {
                    "display_id": getattr(h, 'display_id', master_id) or master_id,
                    "road_name": getattr(h, 'road_name', 'Unknown Road') or "Unknown Road",
                    "image_url": h.image_url,
                    "latitude": safe_float(h.latitude, 0.0),
                    "longitude": safe_float(h.longitude, 0.0),
                    "priority": getattr(h, 'priority', 'Medium') or "Medium",
                    "risk_score": safe_int(getattr(h, 'risk_score', 50), 50),
                    "severity": getattr(h, 'severity', 'Medium') or "Medium",
                    "confidence": safe_float(getattr(h, 'confidence', 0), 0.0),
                    "created_at": h.created_at,
                    "report_count": safe_int(getattr(h, 'report_count', 1), 1)
                }
                print(f"Fallback Used: False")
            else:
                # Registry Cache MISS -> Fallback to Database
                print(f"Registry HIT/MISS: MISS for key {master_id}")
                fallback_h = _get_hazard_details(hid_str)
                if fallback_h:
                    is_fallback = True
                    hazard_data = {
                        "display_id": master_id,
                        "road_name": "Unknown Road",
                        "image_url": fallback_h.get("image"), # _get_hazard_details returns 'image'
                        "latitude": safe_float(fallback_h.get("latitude"), 0.0),
                        "longitude": safe_float(fallback_h.get("longitude"), 0.0),
                        "priority": fallback_h.get("severity", "Medium").capitalize() if fallback_h.get("severity") else "Medium",
                        "risk_score": 50, # Default risk for fallback
                        "severity": fallback_h.get("severity", "Medium") or "Medium",
                        "confidence": safe_float(fallback_h.get("confidence"), 0.0),
                        "created_at": fallback_h.get("created_at"),
                        "report_count": safe_int(fallback_h.get("reports_count"), 1)
                    }
                    print(f"Fallback Used: True")
                else:
                    print(f"Fallback Used: FAILED")
                    print("Job Skipped: True")
                    print("==============================")
                    skipped_count += 1
                    continue # Hazard truly doesn't exist
                
            url = hazard_data.get("image_url")
            # _get_hazard_details already normalizes url, but we'll apply safety check anyway
            if url and not url.startswith("http") and not url.startswith("/static"):
                url = f"{Config.SUPABASE_URL.rstrip('/')}/storage/v1/object/public/pothole-images/{url}"
                
            if url:
                img_name = url.strip().split('/')[-1]
                if img_name in seen_images:
                    print(f"Job Skipped: True (Duplicate image {img_name})")
                    print("==============================")
                    skipped_count += 1
                    continue
                seen_images.add(img_name)
            
            risk = hazard_data["risk_score"]
                
            if risk >= 90: repair_time = 50
            elif risk >= 70: repair_time = 40
            elif risk >= 50: repair_time = 30
            else: repair_time = 20
            
            lat = hazard_data["latitude"]
            lon = hazard_data["longitude"]
            conf = hazard_data["confidence"]
            
            print(f"Confidence Value: {conf}")
            print(f"Latitude: {lat}")
            print(f"Longitude: {lon}")
                
            jobs.append({
                "hazard_id": master_id,
                "display_id": hazard_data.get("display_id"),
                "road_name": hazard_data.get("road_name"),
                "image": url,
                "latitude": lat,
                "longitude": lon,
                "distance_km": None, # Frontend managed
                "eta_minutes": None, # Frontend managed
                "repair_time_minutes": repair_time,
                "priority": hazard_data.get("priority"),
                "risk_score": risk,
                "severity": str(hazard_data.get("severity")).capitalize(),
                "confidence_percent": int(round(conf * 100)),
                "waiting_time": None, # Frontend managed
                "created_at": hazard_data.get("created_at"),
                "report_count": hazard_data.get("report_count"),
                "assignment_id": assignment_id,
                "assignment_status": a.get("status")
            })
            print("Job Added: True")
            print("==============================")
            processed_count += 1
            
        except Exception as e:
            print("Job Skipped: True")
            print(f"Exception: {e}")
            print(traceback.format_exc())
            print("==============================")
            skipped_count += 1
            continue
            
    print(f"\nAssignments fetched: {len(assignments)}")
    print(f"Assignments processed: {processed_count}")
    print(f"Assignments skipped: {skipped_count}")
    print(f"Jobs returned: {len(jobs)}")
    print(f"Processing time: {time.time() - start_time:.4f} seconds\n")
    return jobs

@worker_dispatch_api.route("/jobs/<job_id>/accept", methods=["POST"])
@worker_api
def accept_job(job_id, sql_log):
    worker_id = session.get("user_id")
    worker_name = session.get("name")
    worker_email = session.get("email", "")
    
    if _get_active_assignment(worker_id, sql_log):
        return {"success": False, "message": "You already have an active assignment."}, 400
        
    # Normalize job_id
    master_id = str(job_id)
    if "-" in master_id:
        hazard_id_int = int(master_id.split("-")[1])
        hazard_source = 'user_reports' if master_id.startswith('USER') else 'ai_detections'
    else:
        hazard_id_int = int(master_id)
        # Default fallback, though shouldn't happen with new workflow
        hazard_source = 'user_reports'
        master_id = f"USER-{hazard_id_int}"
        
    print("=================================")
    print("Worker Accept Job")
    print(f"Worker ID: {worker_id}")
    print(f"Assignment ID: N/A")
    print(f"Hazard ID: {master_id}")
        
    # Check registry cache purely for logging
    from services.hazard_registry import registry_cache, recalculate_single_hazard
    
    with registry_cache.lock:
        h = registry_cache.data.get(master_id)
        
    if h:
        print("Registry HIT: True")
        print("Registry MISS: False")
        print("Database Fallback Used: False")
    else:
        print("Registry HIT: False")
        print("Registry MISS: True")
        # Ensure it exists in the database before proceeding
        fallback_h = _get_hazard_details(hazard_id_int)
        if not fallback_h:
            print("Database Fallback Used: FAILED")
            print("=================================")
            return {"success": False, "message": "Hazard not found in database."}, 404
        print("Database Fallback Used: True")
        
    # The assignments table is the source of truth
    from routes.api import get_supabase
    import datetime
    supabase = get_supabase()
    
    try:
        # Read assignment from Supabase
        a_res = supabase.table("assignments").select("*").eq("hazard_id", hazard_id_int).order("id", desc=True).limit(1).execute()
        
        if not a_res.data:
            return {"success": False, "message": "Assignment not found."}, 404
            
        assignment = a_res.data[0]
        status = assignment.get("status")
        assignment_id = assignment.get("id")
        print(f"Assignment Status Before: {status}")
        
        # Validate status constraints
        if status in ["Accepted", "Travelling", "Reached Site", "Repair Started", "Repair Completed", "Waiting Verification", "Verified", "Rejected"]:
            return {"success": False, "message": f"Already in progress or completed ({status})."}, 409
            
        if status not in ["Available", "Assigned", "Needs Rework"]:
            return {"success": False, "message": "Invalid state for accepting."}, 409
            
        # Verify it's either available, or assigned to THIS worker
        if status in ["Assigned", "Needs Rework"] and str(assignment.get("worker_id")) != str(worker_id):
            return {"success": False, "message": "Assigned to another worker."}, 409

        # Update assignment
        upd_res = supabase.table("assignments").update({
            "status": "Accepted",
            "worker_id": worker_id,
            "worker_name": worker_name,
            "worker_email": worker_email,
            "accepted_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }).eq("id", assignment_id).execute()
        
        accepted_row = upd_res.data[0] if upd_res.data else {}
        print(f"Assignment Status After: Accepted")

    except Exception as e:
        print(f"[SQL ERROR] {str(e)}")
        return {"success": False, "message": "Database conflict."}, 409
    
    # Update Supabase Worker Status
    supabase.table("users").update({"worker_status": "Busy"}).eq("id", worker_id).execute()
    
    print(f"[WORKFLOW] [STATUS CHANGED] Hazard {master_id} | Available -> Accepted | worker={worker_name}")
    print(f"[WORKFLOW] [ASSIGNMENT UPDATED] Worker {worker_id} accepted job {master_id}.")
    
    try:
        from routes.api import sync_hazard_cache
        # Instantly patch the assignment in the cache so /api/alerts reflects Accepted status immediately
        sync_hazard_cache(master_id, hazard_id_int)
        print("Registry Updated: True")
        print(f"[WORKFLOW] [ALERT CACHE REFRESHED] {master_id} updated to Accepted in registry.")
        print("Completed Successfully: True")
        print("=================================")
    except Exception as e:
        print("Registry Updated: False")
        print(f"Completed Successfully: False ({e})")
        print("=================================")
        print(f"[!] Error updating hazard cache on accept: {e}")
    
    return {"success": True, "message": "Job Accepted"}

@worker_dispatch_api.route("/active-job", methods=["GET"])
@worker_api
def get_active_job(sql_log):
    worker_id = session.get("user_id")
    assignment = _get_active_assignment(worker_id, sql_log)
    
    if not assignment:
        return None
        
    hazard = _get_hazard_details(assignment["hazard_id"], assignment.get("hazard_source"))
    if hazard:
        assignment["hazard"] = hazard
        
    return assignment

@worker_dispatch_api.route("/jobs/<job_id>/status", methods=["POST"])
@worker_api
def update_status(job_id, sql_log):
    print("Hazard ID:", job_id)
    data = request.json or {}
    new_status = data.get("status")
    worker_id = session.get("user_id")
    
    valid_statuses = ["Travelling", "Reached Site", "Repair Started", "Repair Completed", "Waiting Verification"]
    if new_status not in valid_statuses:
        return {"success": False, "message": "Invalid status"}, 400
        
    from routes.api import get_supabase
    supabase = get_supabase()
    
    a_res = supabase.table("assignments").select("*").eq("hazard_id", job_id).eq("worker_id", worker_id).execute()
    if not a_res.data:
        return {"success": False, "message": "Assignment not found or unauthorized"}, 404
        
    row = a_res.data[0]
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    update_data = {"status": new_status}
    
    if new_status == "Travelling":
        update_data["travelling_at"] = now
    elif new_status == "Reached Site":
        update_data["reached_at"] = now
    elif new_status == "Repair Started":
        update_data["repair_started_at"] = now
    elif new_status == "Repair Completed":
        update_data["repair_completed_at"] = now
    elif new_status == "Waiting Verification":
        update_data["verified_at"] = now

    supabase.table("assignments").update(update_data).eq("hazard_id", job_id).eq("worker_id", worker_id).execute()
    
    if new_status == "Waiting Verification":
        supabase = get_supabase()
        supabase.table("users").update({"worker_status": "Available"}).eq("id", worker_id).execute()

    print(f"[WORKFLOW] [STATUS CHANGED] Hazard {job_id} | -> {new_status} | worker={worker_id}")
    print(f"[WORKFLOW] [ASSIGNMENT UPDATED] update_data={update_data}")
    
    try:
        from routes.api import sync_hazard_cache
        master_id = f"USER-{job_id}" if row["hazard_source"] == 'user_reports' else f"AI-{job_id}"
        
        # Fetch the COMPLETE updated assignment row
        updated = (
            supabase.table("assignments")
            .select("*")
            .eq("hazard_id", job_id)
            .eq("worker_id", worker_id)
            .single()
            .execute()
        )
        patched_assignment = updated.data
        sync_hazard_cache(master_id, int(job_id))
        print(f"[WORKFLOW] [ALERT CACHE REFRESHED] {master_id} updated to {new_status} in registry.")

        from services.hazard_registry import (
            registry_cache,
            recalculate_single_hazard_async
        )

        recalculate_single_hazard_async(
            master_id,
            patched_assignment,
            row.get("hazard_source"),
            "status_update"
        )

        registry_cache.invalidate()

        try:
            from routes.api import global_alerts_cache
            global_alerts_cache["data"] = None
        except Exception:
            pass
    except Exception as e:
        print(f"[!] Error updating hazard cache on status update: {e}")
    
    return {"success": True, "message": "Status updated"}

@worker_dispatch_api.route("/jobs/<job_id>/location", methods=["POST"])
@worker_api
def update_location(job_id, sql_log):
    data = request.json or {}
    lat = data.get("lat")
    lon = data.get("lon")
    worker_id = session.get("user_id")
    
    if lat is None or lon is None:
        return {"success": False, "message": "Missing coordinates"}, 400
        
    from routes.api import get_supabase
    supabase = get_supabase()
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    supabase.table("assignments").update({
        "current_lat": lat,
        "current_lon": lon,
        "last_location_update": now
    }).eq("hazard_id", job_id).eq("worker_id", worker_id).eq("status", "Travelling").execute()
    
    return {"success": True}

@worker_dispatch_api.route("/notifications", methods=["GET"])
@worker_api
def get_notifications(sql_log):
    worker_id = session.get("user_id")
    
    from routes.api import get_supabase
    supabase = get_supabase()
    
    res = supabase.table("assignments").select("*") \
        .eq("worker_id", worker_id) \
        .order("assigned_time", desc=True) \
        .limit(10).execute()
        
    rows = res.data if res.data else []
    
    notifs = []
    for r in rows:
        hz_id = r["hazard_id"]
        status = r["status"]
        if status == 'Verified':
            notifs.append({
                "title": f"Repair Verified: JOB-{hz_id}",
                "message": "Your work has been approved by the Admin team. Great job!",
                "time": r["verification_completed"] or r["repair_completed_at"],
                "icon": "fa-check",
                "type": "success"
            })
        elif status == 'Rejected':
            notifs.append({
                "title": f"Repair Rejected: JOB-{hz_id}",
                "message": "The Admin team has rejected your repair. Please review the notes.",
                "time": r["verification_completed"] or r["repair_completed_at"],
                "icon": "fa-triangle-exclamation",
                "type": "danger"
            })
            
    notifs.append({
        "title": "System Announcement",
        "message": "Welcome to the VisionaryRoad Dispatch System. Ensure GPS is enabled.",
        "time": datetime.datetime.now().isoformat(),
        "icon": "fa-bullhorn",
        "type": "info"
    })
    
    return notifs

@worker_dispatch_api.route("/jobs/<job_id>/cancel", methods=["POST"])
@worker_api
def cancel_job(job_id, sql_log):
    data = request.json or {}
    reason = data.get("reason", "Cancelled by worker")
    worker_id = session.get("user_id")
    
    from routes.api import get_supabase
    supabase = get_supabase()
    
    a_res = supabase.table("assignments").select("status").eq("hazard_id", job_id).eq("worker_id", worker_id).execute()
    if not a_res.data:
        return {"success": False, "message": "Assignment not found"}, 404
        
    row = a_res.data[0]
    if row["status"] in ["Verified"]:
        return {"success": False, "message": "Cannot cancel a verified job"}, 400
        
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    payload = {
        "status": "Available",
        "worker_id": None,
        "worker_name": None,
        "worker_email": None,
        "accepted_at": None,
        "cancelled_at": now,
        "verification_status": "Pending"
    }
    
    res = supabase.table("assignments").update(payload).eq("hazard_id", job_id).execute()
    
    print("========== CANCEL JOB ==========")
    print(f"Hazard ID: {job_id}")
    print(f"Worker ID: {worker_id}")
    print(f"Old Status: {row['status']}")
    print(f"New Status: Available")
    print(f"[WORKFLOW] [STATUS CHANGED] Hazard {job_id} | {row['status']} -> Available (Worker Cancelled)")
    print("===============================")
    
    supabase = get_supabase()
    supabase.table("users").update({"worker_status": "Available"}).eq("id", worker_id).execute()

    try:
        from routes.api import sync_hazard_cache
        # Determine master_id from assignment source
        source_res = supabase.table("assignments").select("hazard_source").eq("hazard_id", job_id).execute()
        h_source = source_res.data[0].get("hazard_source", "AI") if source_res.data else "AI"
        master_id = f"USER-{job_id}" if h_source == 'user_reports' else f"AI-{job_id}"
        
        sync_hazard_cache(master_id, int(job_id))
        print(f"[WORKFLOW] [ALERT CACHE REFRESHED] {master_id} returned to Available in registry.")
    except Exception as e:
        print(f"[!] Error updating hazard cache on cancel: {e}")
    
    return {"success": True, "message": "Job cancelled and returned to pool"}

@worker_dispatch_api.route("/history", methods=["GET"])
@worker_api
def get_history(sql_log):
    worker_id = session.get("user_id")
    
    from routes.api import get_supabase
    supabase = get_supabase()
    
    res = supabase.table("assignments").select("*") \
        .eq("worker_id", worker_id) \
        .in_("status", ["Completed", "Verified", "Waiting Verification", "Needs Rework", "Rejected"]) \
        .order("repair_completed_at", desc=True).execute()
        
    rows = res.data if res.data else []
    
    history = []
    for r in rows:
        hz = _get_hazard_details(r["hazard_id"], r.get("hazard_source"))
        if hz:
            r["hazard"] = hz
        history.append(r)
        
    return history

@worker_dispatch_api.route("/dashboard-stats", methods=["GET"])
@worker_api
def get_stats(sql_log):
    worker_id = session.get("user_id")
    
    from routes.api import get_supabase
    supabase = get_supabase()
    today_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()[:10]
    
    res1 = supabase.table("assignments").select("id") \
        .eq("worker_id", worker_id) \
        .in_("status", ["Completed", "Verified", "Waiting Verification"]) \
        .gte("repair_completed_at", f"{today_iso}T00:00:00") \
        .lte("repair_completed_at", f"{today_iso}T23:59:59").execute()
    completed_today = len(res1.data) if res1.data else 0
    
    res2 = supabase.table("assignments").select("repair_started_at, repair_completed_at") \
        .eq("worker_id", worker_id) \
        .in_("status", ["Completed", "Verified", "Waiting Verification"]) \
        .not_.is_("repair_started_at", "null") \
        .not_.is_("repair_completed_at", "null").execute()
    times = res2.data if res2.data else []
    
    avg_time = 45 
    if times:
        total_mins = 0
        valid = 0
        for t in times:
            try:
                start = datetime.datetime.fromisoformat(t["repair_started_at"])
                end = datetime.datetime.fromisoformat(t["repair_completed_at"])
                total_mins += (end - start).total_seconds() / 60
                valid += 1
            except: pass
        if valid > 0:
            avg_time = int(total_mins / valid)
            
    active = _get_active_assignment(worker_id, sql_log)
    
    return {
        "completed_today": completed_today,
        "average_repair_time": avg_time,
        "has_active_assignment": active is not None
    }

@worker_dispatch_api.route("/jobs/<job_id>/upload-photo", methods=["POST"])
@worker_api
def upload_photo(job_id, sql_log):
    worker_id = session.get("user_id")
    photo_type = request.form.get("type") # 'before' or 'after'
    file = request.files.get("photo")
    
    if not file or not photo_type:
        return {"success": False, "message": "Missing file or type"}, 400
        
    # Read metadata
    lat = request.form.get("lat")
    lon = request.form.get("lon")
    acc = request.form.get("accuracy")
    ts_ms = request.form.get("timestamp")
    
    parsed_ts = None
    if ts_ms:
        try:
            import datetime
            parsed_ts = datetime.datetime.fromtimestamp(float(ts_ms) / 1000.0, tz=datetime.timezone.utc).isoformat()
        except:
            parsed_ts = None
            
    # Try to parse float for gps
    p_lat = float(lat) if lat else None
    p_lon = float(lon) if lon else None
    p_acc = float(acc) if acc else None
        
    try:
        from werkzeug.utils import secure_filename
        import datetime
        ext = file.filename.rsplit(".", 1)[1].lower() if "." in file.filename else "jpg"
        fname = f"worker_{worker_id}_{job_id}_{photo_type}_{int(datetime.datetime.now().timestamp())}.{ext}"
        
        supabase = get_supabase()
        file_bytes = file.read()
        
        try:
            # We'll put worker photos in pothole-images bucket to keep them accessible to the admin UI easily
            supabase.storage.from_("pothole-images").upload(fname, file_bytes, {"content-type": file.content_type})
        except Exception as e:
            print("Supabase Upload Error:", e)
            return {"success": False, "message": "Failed to upload to cloud storage"}, 500
            
        url = supabase.storage.from_("pothole-images").get_public_url(fname)
        
        url = supabase.storage.from_("pothole-images").get_public_url(fname)
        
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        # Real AI Verification using loaded YOLO model
        from routes.ai import load_model
        import numpy as np
        import cv2
        import time
        
        # Keep inference engine alive, model is loaded once at Flask startup
        model = load_model()
        
        nparr = np.frombuffer(file_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        _t0 = time.time()
        results = model.predict(source=img, imgsz=640, conf=0.20, verbose=False)
        _t_ms = (time.time() - _t0) * 1000
        print(f"[YOLO INFERENCE] Type: {photo_type}, Time: {_t_ms:.2f}ms")
        
        has_defect = False
        best_conf = 0.0
        best_box = None
        
        for r in results:
            if r.boxes is not None:
                for box in r.boxes:
                    conf = float(box.conf[0])
                    has_defect = True
                    if conf > best_conf:
                        best_conf = conf
                        best_box = box.xyxy[0].tolist()
                        
        ai_score = int(best_conf * 100)
        is_verified = False
        ai_message = ""
        
        print("========== AI VERIFICATION ==========")
        print(f"Assignment ID: {job_id}")
        print(f"Hazard ID: {job_id}")
        print(f"Worker ID: {worker_id}")
        print(f"Photo Type: {photo_type}")
        print(f"AI Result: has_defect={has_defect}, score={ai_score}")
        
        # Determine success flag for storing
        stored_successfully = "YES" if url else "NO"
        
        print("\n-----------------------------------------")
        print("WORKER PHOTO METADATA")
        print("-----------------------------------------")
        print(f"Worker ID     : {worker_id}")
        print(f"Assignment ID : {job_id}")
        print(f"Photo Type    : {photo_type}")
        print(f"Latitude      : {p_lat}")
        print(f"Longitude     : {p_lon}")
        print(f"Accuracy      : {p_acc}")
        print(f"Timestamp     : {parsed_ts}")
        print(f"Stored Successfully: {stored_successfully}")
        print("-----------------------------------------\n")
        
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        if photo_type == "before":
            if has_defect:
                is_verified = True
                ai_message = f"Hazard confirmed ({ai_score}% confidence)."
                payload = {
                    "before_photo": url,
                    "verification_status": "Before Photo Verified",
                    "verification_notes": "AI detected pothole successfully.",
                    "reached_at": now,
                    "repair_started_at": now,   # mark repair start for duration calculation
                    "status": "Repair Started",
                    "before_photo_lat": p_lat,
                    "before_photo_lon": p_lon,
                    "before_photo_accuracy": p_acc,
                    "before_photo_timestamp": parsed_ts
                }
                print(f"Database Update Payload: {payload}")
                supabase.table("assignments").update(payload).eq("hazard_id", job_id).eq("worker_id", worker_id).execute()
            else:
                is_verified = False
                ai_message = "No pothole detected. Please capture a clearer image."
                # Do NOT update nonexistent columns.
                print("Database Update Payload: None (verification failed)")
        else: # After photo
            if has_defect:
                is_verified = False
                ai_message = f"Repair verification failed. Road damage is still visible ({ai_score}% confidence). Please repair again and upload a new after photo."
                print("Database Update Payload: None (verification failed)")
            else:
                is_verified = True
                ai_score = 100
                ai_message = "No defect detected. Repair quality standards met."
                payload = {
                    "after_photo": url,
                    "verification_status": "Pending Admin Review",
                    "verification_notes": "AI verification passed.",
                    "repair_completed_at": now,
                    "status": "Waiting Verification",
                    "after_photo_lat": p_lat,
                    "after_photo_lon": p_lon,
                    "after_photo_accuracy": p_acc,
                    "after_photo_timestamp": parsed_ts
                }
                print(f"Database Update Payload: {payload}")
                supabase.table("assignments").update(payload).eq("hazard_id", job_id).eq("worker_id", worker_id).execute()
                # Free up worker
                supabase.table("users").update({"worker_status": "Available"}).eq("id", worker_id).execute()
                
        h_res = supabase.table("assignments").select("hazard_source").eq("hazard_id", job_id).execute()
        row = h_res.data[0] if h_res.data else None
        
        if row:
            master_id = f"USER-{job_id}" if row["hazard_source"] == 'user_reports' else f"AI-{job_id}"
            try:
                # Fetch the full assignment row for instant patch
                full_row_res = supabase.table("assignments").select("*").eq("hazard_id", job_id).eq("worker_id", worker_id).execute()
                full_row = full_row_res.data[0] if full_row_res.data else None
                
                from routes.api import sync_hazard_cache
                if full_row:
                    print(f"[WORKFLOW] [STATUS CHANGED] Hazard {master_id} | photo_type={photo_type} | -> {full_row.get('status')}")
                    print(f"[WORKFLOW] [ASSIGNMENT UPDATED] {master_id} photo upload processed.")
                    sync_hazard_cache(master_id, int(job_id))
                    print(f"[WORKFLOW] [ALERT CACHE REFRESHED] {master_id} photo state updated in registry.")
                    
                    from services.hazard_registry import (
                        registry_cache,
                        recalculate_single_hazard_async
                    )

                    recalculate_single_hazard_async(
                        master_id,
                        full_row,
                        row.get("hazard_source"),
                        "photo_upload"
                    )

                    registry_cache.invalidate()

                    try:
                        from routes.api import global_alerts_cache
                        global_alerts_cache["data"] = None
                    except Exception:
                        pass
            except Exception as e:
                print(f"[!] Error updating hazard cache on photo upload: {e}")
        
        status_code = 200 if is_verified else 422
        return {
            "success": is_verified,
            "verification": {
                "verified": is_verified,
                "score": ai_score,
                "message": ai_message,
                "processing_time_ms": _t_ms,
                "bbox": best_box
            },
            "message": ai_message
        }, status_code
            
    except Exception as e:
        print("Upload Photo Error:", e)
        return {"success": False, "message": str(e)}, 500

@worker_dispatch_api.route("/live-yolo", methods=["POST"])
@worker_api
def live_yolo(sql_log):
    file = request.files.get("photo")
    if not file:
        return {"success": False}, 400
        
    try:
        from routes.ai import load_model, run_inference
        import numpy as np
        import cv2
        
        model = load_model()
        file_bytes = file.read()
        nparr = np.frombuffer(file_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        results, detections = run_inference(model, img)
        
        best_box = None
        best_conf = 0.0
        
        for d in detections:
            if d.get("confidence", 0) > best_conf:
                best_conf = d["confidence"]
                best_box = d.get("box")
                
        return {"success": True, "bbox": best_box, "confidence": best_conf}
    except Exception as e:
        print("Live YOLO Error:", e)
        return {"success": False}, 500
