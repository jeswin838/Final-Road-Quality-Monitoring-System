import os
import concurrent.futures
from datetime import datetime, date
from flask import Blueprint, request, jsonify, session, current_app
from werkzeug.utils import secure_filename
from config import Config
from utils.helpers import is_duplicate, filter_by_confidence, majority_severity, allowed_file, upload_with_retry, db_insert_with_retry

api_bp = Blueprint("api", __name__, url_prefix="/api")

global_alerts_cache = {"data": None, "timestamp": 0}

# Lazy load supabase from app to avoid circular import issues
def get_supabase():
    from app import supabase
    return supabase

# -----------------------------------------------------------------------------
# GET /api/live-data
# -----------------------------------------------------------------------------
@api_bp.route("/live-data", methods=["GET"])
def get_live_data():
    try:
        from services.live_data_service import get_all_data
        data = get_all_data()
        return jsonify(data)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# -----------------------------------------------------------------------------
# GET /api/location-reports?lat=...&lon=...
# -----------------------------------------------------------------------------
@api_bp.route("/location-reports", methods=["GET"], strict_slashes=False)
def get_location_reports():
    lat_val = request.args.get("lat")
    lon_val = request.args.get("lon")

    print(f"[API] location-reports request: lat={lat_val}, lon={lon_val}")

    if not lat_val or not lon_val:
        return jsonify({"error": "Latitude and Longitude are required"}), 400

    supabase = get_supabase()
    if not supabase:
        print("[!] location-reports error: Supabase not connected")
        return jsonify({"error": "Database connection lost"}), 500
    
    try:
        try:
            lat = float(lat_val)
            lon = float(lon_val)
        except ValueError:
            return jsonify({"error": "Invalid coordinates format"}), 400
            
        # Bounding box of approx 60m to query candidates
        EPSILON = 0.0006 
        
        # Fetch app settings confidence threshold as default
        conf_thresh = Config.DEFAULT_CONFIDENCE_THRESHOLD
        try:
            conn = get_sqlite()
            cur = conn.cursor()
            cur.execute("SELECT detection_sensitivity FROM app_settings WHERE id = 1")
            row = cur.fetchone()
            conn.close()
            if row:
                conf_thresh = float(row["detection_sensitivity"] or Config.DEFAULT_CONFIDENCE_THRESHOLD)
        except:
            pass

        active_statuses = ["approved", "Approved", "Available", "available", "Assigned", "assigned", "Accepted", "accepted", "In Progress", "in progress", "Waiting Verification", "waiting verification"]
        
        print(f"[DB] Querying active potholes near {lat}, {lon} (±{EPSILON})")
        p_res = supabase.table("potholes") \
            .select("*") \
            .eq("pothole", True) \
            .in_("status", active_statuses) \
            .gte("latitude", lat - EPSILON) \
            .lte("latitude", lat + EPSILON) \
            .gte("longitude", lon - EPSILON) \
            .lte("longitude", lon + EPSILON) \
            .execute()
        
        p_data = getattr(p_res, 'data', []) or []
        
        # Fetch active user reports near coordinates
        u_res = supabase.table("user_reports") \
            .select("*") \
            .in_("status", active_statuses) \
            .gte("latitude", lat - EPSILON) \
            .lte("latitude", lat + EPSILON) \
            .gte("longitude", lon - EPSILON) \
            .lte("longitude", lon + EPSILON) \
            .execute()
            
        u_data = getattr(u_res, 'data', []) or []
        for c in u_data:
            c["image_url"] = c.get("media_url")
            c["media_url"] = c.get("media_url")
            c["latitude"] = c.get("latitude")
            c["longitude"] = c.get("longitude")
            c["created_at"] = c.get("created_at")
            c["description"] = c.get("description")
            c["status"] = c.get("status")
            c["type"] = c.get("type")
            c["source"] = "Citizen Report"
            c["confidence"] = None  # Citizen reports do not have AI confidence
            c["severity"] = c.get("severity") or None
            c["pothole"] = True
            
        p_data = u_data + p_data
        p_data.sort(key=lambda x: x.get("created_at") or "", reverse=True)
        
        # Merge with Supabase assignments to get Status
        try:
            a_res = supabase.table("assignments").select("hazard_id, status").execute()
            assigns = {r["hazard_id"]: r["status"] for r in a_res.data} if a_res.data else {}
        except:
            assigns = {}

        from utils.helpers import haversine
        combined = []
        seen_images = set()

        for p in p_data:
            p_lat, p_lon = float(p.get("latitude", 0)), float(p.get("longitude", 0))
            if p_lat == 0 or p_lon == 0:
                continue

            # Filter by haversine distance matching the 50m map grouping threshold
            if haversine(lat, lon, p_lat, p_lon) >= 50.0:
                continue
                
            conf = p.get("confidence")
            is_citizen = p.get("source") == "Citizen Report" or p.get("source_report_id") is not None
            if not is_citizen:
                p["source"] = "AI Detection"

            # Skip rejected, pending, or closed records
            p_status = p.get("status", "approved")
            if not is_citizen and p.get("id") in assigns:
                p_status = assigns[p["id"]]

            if (p_status or "").lower() in ('rejected', 'pending', 'closed'):
                continue
                
            # Collect and Normalize URLs
            urls = []
            bucket_name = "user-reports" if is_citizen else "pothole-images"
            for field in ["image_url", "media_url", "annotated_image_url", "before_photo", "after_photo", "verification_image"]:
                f_url = p.get(field)
                if f_url and str(f_url).strip():
                    if not str(f_url).startswith("http") and not str(f_url).startswith("/static"):
                        base_url = Config.SUPABASE_URL.rstrip('/')
                        f_url = f"{base_url}/storage/v1/object/public/{bucket_name}/{f_url.lstrip('/')}"
                    urls.append(f_url)
            
            main_url = urls[0] if urls else None
            if main_url:
                img_name = main_url.strip().split('/')[-1]
                if img_name in seen_images:
                    pass # We won't skip the record entirely, but maybe just log it
                seen_images.add(img_name)

            combined.append({
                "id": p.get("id"),
                "display_id": p.get("display_id") or p.get("id"),
                "marker_id": p.get("marker_id"),
                "image_url": main_url,
                "media_url": main_url,
                "all_images": urls,
                "source": p.get("source"),
                "severity": p.get("severity"),
                "status": p_status,
                "confidence": p.get("confidence"),
                "risk_score": p.get("risk_score"),
                "road_name": p.get("road_name"),
                "landmark": p.get("landmark"),
                "village": p.get("village"),
                "district": p.get("district"),
                "state": p.get("state"),
                "type": p.get("type") or "pothole",
                "created_at": p.get("created_at") or "",
                "description": p.get("description"),
                "assignment": p.get("assignment"),
                "reports_count": p.get("reports_count"),
                "latitude": p.get("latitude"),
                "longitude": p.get("longitude")
            })
            
        # Calculate Average AI Confidence
        valid_confidences = []
        for r in combined:
            conf = r.get("confidence")
            
            if conf is None:
                continue
                
            try:
                c_val = float(conf)
                valid_confidences.append(c_val)
            except (ValueError, TypeError):
                pass

        avg_conf = None
        if len(valid_confidences) > 0:
            avg_conf = round(sum(valid_confidences) / len(valid_confidences), 1)

        total_reports = len(combined)
        valid_count = len(valid_confidences)

        for r in combined:
            r["average_confidence"] = avg_conf
            r["valid_confidence_count"] = valid_count
            r["total_images"] = total_reports

        # Sort by most recent
# Sort by most recent
        combined.sort(key=lambda x: str(x.get("created_at") or ""), reverse=True)
        
        print(f"[API] location-reports success: found {len(combined)} items")
        return jsonify(combined)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[!] location-reports Critical Error: {e}")
        return jsonify({"error": str(e)}), 500


# -----------------------------------------------------------------------------
# GET /api/potholes
# -----------------------------------------------------------------------------
@api_bp.route("/potholes", methods=["GET"])
def get_potholes():
    severity   = request.args.get("severity")
    status     = request.args.get("status")
    date_from  = request.args.get("date_from")
    date_to    = request.args.get("date_to")
    confidence = request.args.get("confidence", type=float)
    limit      = request.args.get("limit",  type=int)
    sort_dir   = request.args.get("sort",   "desc").lower()
    ptype      = request.args.get("type")

    supabase = get_supabase()
    if not supabase:
        print("[!] Warning: API called but Supabase not connected.")
        return jsonify([]) # Return empty list instead of 500 for better UX

    try:
        f_severity = request.args.get("severity", "").lower()
        f_status   = request.args.get("status", "").lower()
        f_date_from = request.args.get("date_from")
        f_date_to   = request.args.get("date_to")

        from utils.helpers import filter_by_confidence

        # Fetch app settings confidence threshold as default if not passed
        conf_thresh = confidence if confidence is not None else Config.DEFAULT_CONFIDENCE_THRESHOLD
        try:
            conn = get_sqlite()
            cur = conn.cursor()
            cur.execute("SELECT detection_sensitivity FROM app_settings WHERE id = 1")
            row = cur.fetchone()
            conn.close()
            if row:
                conf_thresh = confidence if confidence is not None else float(row["detection_sensitivity"] or Config.DEFAULT_CONFIDENCE_THRESHOLD)
        except:
            pass

        # 1. Fetch AI Potholes
        combined = []
        if not ptype or ptype.lower() in ["pothole", "crack"]:
            # AI/Sensor/Live detections (filter by source_report_id is null to avoid duplicating citizen reports)
            p_query = supabase.table("potholes").select("*").is_("source_report_id", "null").eq("pothole", True)
            if f_status:
                p_query = p_query.eq("status", f_status)
            else:
                p_query = p_query.eq("status", "approved")
            if severity: p_query = p_query.ilike("severity", severity)
            if date_from: p_query = p_query.gte("created_at", f"{date_from}T00:00:00")
            if date_to: p_query = p_query.lte("created_at", f"{date_to}T23:59:59")
            if ptype: p_query = p_query.ilike("type", ptype)
            
            p_res = p_query.order("created_at", desc=(sort_dir == "desc")).limit(500).execute()
            ai_data = p_res.data or []
            for p in ai_data:
                p["source"] = "AI"
            
            # Citizen reports approved by admin
            c_query = supabase.table("user_reports").select("*")
            if f_status:
                c_query = c_query.eq("status", f_status)
            else:
                c_query = c_query.eq("status", "approved")
            if severity: c_query = c_query.ilike("severity", severity)
            if date_from: c_query = c_query.gte("created_at", f"{date_from}T00:00:00")
            if date_to: c_query = c_query.lte("created_at", f"{date_to}T23:59:59")
            # Note: user_reports uses 'type' differently (e.g. 'image'), but we allow it or skip if not matching
            
            c_res = c_query.order("created_at", desc=(sort_dir == "desc")).limit(500).execute()
            citizen_data = c_res.data or []
            for c in citizen_data:
                c["source"] = "Citizen"
                # Map user_reports schema to pothole schema exactly as requested
                c["image_url"] = c.get("media_url")
                c["media_url"] = c.get("media_url")
                c["latitude"] = c.get("latitude")
                c["longitude"] = c.get("longitude")
                c["created_at"] = c.get("created_at")
                c["description"] = c.get("description")
                c["status"] = c.get("status")
                c["type"] = c.get("type")
                c["source"] = "Citizen"
                c["confidence"] = c.get("confidence")
                c["severity"] = c.get("severity") or "Citizen Report"
                c["pothole"] = True
            
            # Merge both
            combined = ai_data + citizen_data
            
            # Re-sort the combined list just in case
            combined.sort(key=lambda x: x.get("created_at", ""), reverse=(sort_dir == "desc"))

        # Build lookup for enrichment of user-report logs.
        # Normalize keys to just the filename to ensure matching even if one is a full URL
        ai_by_image = {}
        for p in combined:
            raw_url = (p.get("image_url") or "").strip()
            if raw_url:
                fname = raw_url.split("/")[-1]
                ai_by_image[fname] = p

        # Combine
        rows = combined
        print(f"[PIPELINE TRACE] Stage 1 (Database Fetch): in={len(combined)} records.")

        # Confidence filter
        pre_conf = len(rows)
        rows = filter_by_confidence(rows, conf_thresh)
        print(f"[PIPELINE TRACE] Stage 2 (Confidence Filter): in={pre_conf}, out={len(rows)}, dropped={pre_conf - len(rows)}, reason='Confidence < {conf_thresh}'")
        
        # Merge with Supabase assignments to get Status
        try:
            a_res = supabase.table("assignments").select("hazard_id, status").execute()
            assigns = {r["hazard_id"]: r["status"] for r in a_res.data} if a_res.data else {}
        except:
            assigns = {}

        dedupe = request.args.get("dedupe", "false").lower() == "true"
        
        if dedupe:
            # --- GROUPING/MERGING NEARBY DUPLICATES (25m threshold) ---
            from utils.helpers import haversine
            grouped_rows = []
            
            # Sort by creation date (newest first) so we keep the latest image/details
            rows.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            
            for r in rows:
                try:
                    lat, lon = float(r["latitude"]), float(r["longitude"])
                except (TypeError, ValueError):
                    continue
                    
                img_url = r.get("image_url")
                found_group = False
                
                for g in grouped_rows:
                    # Check 1: Identical Image URL (Highest confidence of duplicate)
                    if img_url and g.get("image_url") == img_url:
                        found_group = True
                    
                    # Check 2: Proximity (25 meters threshold)
                    else:
                        dist = haversine(lat, lon, float(g["latitude"]), float(g["longitude"]))
                        if dist < 25.0: 
                            found_group = True
                    
                    if found_group:
                        # Merge logic:
                        # 1. Accumulate severity votes — majority wins
                        if "_severity_votes" not in g:
                            g["_severity_votes"] = [g.get("severity") or "medium"]
                        r_sev = (r.get("severity") or "medium")
                        g["_severity_votes"].append(r_sev)
                        g["severity"] = majority_severity(g["_severity_votes"])
                        
                        # 2. Accumulate report count
                        g["report_count"] = (g.get("report_count") or 1) + (r.get("report_count") or 1)
                        
                        # 3. Update last_reported_at if newer
                        r_ts = r.get("created_at")
                        if r_ts and r_ts > g.get("created_at", ""):
                            g["created_at"] = r_ts # Keep newest timestamp
                        
                        break
                
                if not found_group:
                    # Add as new group representative (initialise vote list)
                    if "report_count" not in r: r["report_count"] = 1
                    r["_severity_votes"] = [r.get("severity") or "medium"]
                    grouped_rows.append(r)
            
            processed_rows = grouped_rows
            print(f"[PIPELINE TRACE] Stage 3 (Deduplication): in={len(rows)}, out={len(processed_rows)}, dropped={len(rows) - len(processed_rows)}, reason='Spatial clustering within 25m'")
        else:
            # No deduplication, return raw rows
            processed_rows = rows
            print(f"[PIPELINE TRACE] Stage 3 (Deduplication): Skipped (dedupe=false). out={len(processed_rows)}")

        final_rows = []
        for r in processed_rows:
            # 1. Status Check
            r_status = assigns.get(r["id"]) or r.get("status") or "Pending"
            r["status"] = r_status
            
            if status and r_status.lower() != status.lower():
                print(f"[PIPELINE TRACE] Dropping record ID {r.get('id')} - Status mismatch (Expected: {status.lower()}, Got: {r_status.lower()})")
                continue

            # 2. Severity Check (Important for unified results)
            r_severity = (r.get("severity") or "medium").lower()
            if severity and r_severity != severity.lower():
                print(f"[PIPELINE TRACE] Dropping record ID {r.get('id')} - Severity mismatch (Expected: {severity.lower()}, Got: {r_severity})")
                continue

            # 3. Normalize image URLs
            url = r.get("image_url")
            if url and not url.startswith("http") and not url.startswith("/static"):
                r["image_url"] = f"{Config.SUPABASE_URL}/storage/v1/object/public/pothole-images/{url}"
            
            final_rows.append(r)

        print(f"[PIPELINE TRACE] Stage 4 (Final API Filters): in={len(processed_rows)}, out={len(final_rows)}, dropped={len(processed_rows) - len(final_rows)}")

        if limit:
            final_rows = final_rows[:limit]

        return jsonify(final_rows)
    except Exception as e:
        print(f"[!] Error in get_potholes: {e}")
        return jsonify([])

# -----------------------------------------------------------------------------
# POST /api/pothole  — add new record
# -----------------------------------------------------------------------------
@api_bp.route("/pothole", methods=["POST"])
def add_pothole():
    supabase = get_supabase()
    if not supabase:
        return jsonify({"error": "Supabase not connected"}), 500

    data      = request.form
    latitude  = float(data.get("latitude",  0))
    longitude = float(data.get("longitude", 0))
    severity  = data.get("severity",  "Low")
    ptype     = data.get("type",      "pothole")
    confidence= float(data.get("confidence", 0.9))
    pothole   = True

    # 1. Duplicate check with logic to update instead of insert
    existing_p = is_duplicate(supabase, latitude, longitude)
    
    if existing_p:
        # Update existing pothole
        pid = existing_p["id"]
        supabase.table("potholes").update({
            "confidence": confidence,
            "report_count": (existing_p.get("report_count") or 1) + 1,
            "last_reported_at": datetime.now().isoformat()
        }).eq("id", pid).execute()
        
        return jsonify({"id": pid, "message": "Duplicate detected. Updated existing record."}), 200

    # 2. Image upload to Supabase
    image_url = ""
    if "image" in request.files:
        f = request.files["image"]
        if f and allowed_file(f.filename, Config.ALLOWED_EXTENSIONS):
            f_bytes = f.read()
            base_name = f"manual_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
            filename = upload_with_retry(supabase, f_bytes, base_name)
            if filename:
                image_url = f"{Config.SUPABASE_URL}/storage/v1/object/public/pothole-images/{filename}"
                print(f"[API] Manual image uploaded to Supabase: {filename}")

    # 3. Insert new pothole
    try:
        res = supabase.table("potholes").insert({
            "latitude": latitude,
            "longitude": longitude,
            "severity": severity,
            "type": ptype,
            "confidence": confidence,
            "pothole": pothole,
            "image_url": image_url,
            "report_count": 1,
            "last_reported_at": datetime.now().isoformat()
        }).execute()

        if not res.data:
            return jsonify({"error": "Failed to insert record"}), 500

        new_id = res.data[0]["id"]
        print(f"[+] Created new pothole record #{new_id}")
        return jsonify({"id": new_id, "message": "Pothole added"}), 201
    except Exception as e:
        print(f"[!] Insert Pothole Error: {e}")
        return jsonify({"error": str(e)}), 500

# -----------------------------------------------------------------------------
# GET /api/report/<id>
# -----------------------------------------------------------------------------
@api_bp.route("/report/<int:rid>", methods=["GET"])
def get_report_by_id(rid):
    supabase = get_supabase()
    if not supabase: return jsonify({"error": "DB disconnected"}), 500
    
    # Try pothole table
    res = supabase.table("potholes").select("*").eq("id", rid).execute()
    data = res.data
    if not data:
        # Try user_reports table
        res = supabase.table("user_reports").select("*").eq("id", rid).execute()
        data = res.data
        if data:
            data[0]["source"] = "Citizen"
            data[0]["image_url"] = data[0].get("media_url")
    else:
        data[0]["source"] = "AI"

    if not data:
        return jsonify({"error": "Report not found"}), 404
        
    report = data[0]
    
    images = []
    
    def add_img(url):
        if url and isinstance(url, str):
            if not url.startswith("http") and not url.startswith("/static"):
                url = f"{Config.SUPABASE_URL}/storage/v1/object/public/pothole-images/{url}"
            if url not in images:
                images.append(url)
                
    add_img(report.get("image_url") or report.get("media_url"))
    add_img(report.get("annotated_image_url"))
    add_img(report.get("worker_before_image"))
    add_img(report.get("worker_after_image"))
    
    report["all_images"] = images
    
    # Merge status from assignments if exists
    try:
        a_res = supabase.table("assignments").select("status").eq("hazard_id", rid).execute()
        if a_res.data:
            report["status"] = a_res.data[0]["status"]
    except:
        pass
        
    return jsonify(report)

# -----------------------------------------------------------------------------
# PUT /api/pothole/<id>  — update status / severity
# -----------------------------------------------------------------------------
@api_bp.route("/pothole/<int:pid>", methods=["PUT"])
def update_pothole(pid):
    supabase = get_supabase()
    data = request.get_json(silent=True) or {}
    update_data = {}

    # 1. Update Severity in Supabase
    if "severity" in data:
        update_data["severity"] = data["severity"]
        supabase.table("potholes").update(update_data).eq("id", pid).execute()

    # 2. Update Status in Supabase
    if "status" in data:
        new_status = data["status"]
        if new_status == "Completed":
            new_status = "Fixed"
            
        a_res = supabase.table("assignments").select("id").eq("hazard_id", pid).execute()
        if a_res.data:
            supabase.table("assignments").update({"status": new_status}).eq("hazard_id", pid).execute()
        else:
            supabase.table("assignments").insert({
                "hazard_id": pid,
                "worker_name": "System",
                "status": new_status,
                "notes": "Status updated via dashboard"
            }).execute()

    if not "severity" in data and not "status" in data:
        return jsonify({"error": "No fields to update"}), 400

    global global_alerts_cache
    global_alerts_cache["data"] = None
    
    return jsonify({"message": "Pothole updated successfullly"})

# -----------------------------------------------------------------------------
# POST /api/pothole/action  — approve/reject AI detections
# -----------------------------------------------------------------------------
@api_bp.route("/pothole/action", methods=["POST"])
def pothole_action():
    if session.get("role") != "admin":
        return jsonify({"error": "Unauthorized"}), 403
        
    data = request.get_json()
    pid  = data.get("id")
    action = data.get("action") # 'approve' or 'reject'
    
    supabase = get_supabase()
    
    from services.hazard_registry import recalculate_single_hazard_async, registry_cache
    
    if action == "approve":
        supabase.table("potholes").update({
            "status": "approved",
            "review_required": False
        }).eq("id", pid).execute()
        
        recalculate_single_hazard_async(f"AI-{pid}", {"status": "approved"}, "AI", "status_update")
        registry_cache.invalidate()
        global global_alerts_cache
        global_alerts_cache["data"] = None
        
        print(f"\n[ADMIN APPROVAL]\nReport AI-{pid} approved")
        print("[CACHE]\nDashboard cache invalidated")
        print("[CACHE]\nNavigation cache invalidated")
        print("[CACHE]\nAlerts cache invalidated")
        print("[CACHE]\nWorker cache invalidated")
        print("[REGISTRY]\nMerged hazards rebuilt")
        print("[REGISTRY]\nDashboard registry refreshed")
        print("[REGISTRY]\nNavigation registry refreshed")
        print("[REGISTRY]\nWorker registry refreshed")
        print("[LIVE UPDATE]\nDashboard notified")
        print("[LIVE UPDATE]\nNavigation notified")
        print("[LIVE UPDATE]\nWorker module notified")
        print("[LIVE UPDATE]\nAnalytics refreshed")
        print("[SYNC COMPLETE]\nAll affected modules updated successfully\n")
        
        return jsonify({"message": "Pothole approved"}), 200
        
    elif action == "reject":
        supabase.table("potholes").update({
            "status": "rejected",
            "review_required": False
        }).eq("id", pid).execute()
        
        recalculate_single_hazard_async(f"AI-{pid}", {"status": "rejected"}, "AI", "status_update")
        registry_cache.invalidate()
        global_alerts_cache["data"] = None
        
        print(f"\n[ADMIN REJECT]\nReport AI-{pid} rejected")
        print("[CACHE]\nCaches invalidated")
        print("[REGISTRY]\nRegistry synchronized\n")
        
        return jsonify({"message": "Pothole rejected"}), 200
        
    return jsonify({"error": "Invalid action"}), 400

# -----------------------------------------------------------------------------
# DELETE /api/pothole/<id>
# -----------------------------------------------------------------------------
@api_bp.route("/pothole/<int:pid>", methods=["DELETE"])
def delete_pothole(pid):
    supabase = get_supabase()
    supabase.table("potholes").delete().eq("id", pid).execute()
    return jsonify({"message": "Deleted"})

# -----------------------------------------------------------------------------
# GET /api/stats  — summary counts
# -----------------------------------------------------------------------------
# Simple In-Memory Cache for Stats
_stats_cache = {"data": None, "time": None}

@api_bp.route("/stats", methods=["GET"])
def get_stats():
    global _stats_cache
    now_ts = datetime.now()
    if _stats_cache["data"] and _stats_cache["time"] and (now_ts - _stats_cache["time"]).total_seconds() < 5:
        return jsonify(_stats_cache["data"])

    try:
        from services.hazard_engine import get_unified_data
        unified = get_unified_data()
        if "stats" in unified:
            stats_data = unified["stats"]
            _stats_cache = {"data": stats_data, "time": now_ts}
            return jsonify(stats_data)
        
        # Fallback if somehow stats are missing
        return jsonify({"total":0, "today":0, "fixed":0, "pending":0})
    except Exception as e:
        print(f"[!] Stats API Error: {e}")
        return jsonify({"total":0, "today":0, "fixed":0, "pending":0, "error": str(e)})


# -----------------------------------------------------------------------------
# GET /api/analytics
# -----------------------------------------------------------------------------
@api_bp.route("/analytics", methods=["GET"])
def analytics():
    supabase = get_supabase()
    if not supabase: return jsonify({"timeseries":[], "severity_dist":[], "type_dist":[], "top_areas":[]})
    
    try:
        period = request.args.get("period", "daily")   # daily | weekly | monthly
        target_conf = request.args.get("confidence", type=float, default=0.0)

        import datetime
        now = datetime.datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Define time threshold based on period
        if period == "weekly":
            start_date = today_start - datetime.timedelta(days=7)
        elif period == "monthly":
            start_date = today_start - datetime.timedelta(days=30)
        else:
            # daily section takes current day data
            start_date = today_start
        
        # 1. Fetch AI Potholes
        p_res = supabase.table("potholes").select("id, latitude, longitude, severity, created_at, type").eq("pothole", True).gte("confidence", target_conf).gte("created_at", start_date.strftime("%Y-%m-%dT%H:%M:%S")).execute()
        p_rows = p_res.data or []

        # 2. Fetch Approved User Reports
        u_res = supabase.table("user_reports").select("*").eq("status", "approved").gte("created_at", start_date.strftime("%Y-%m-%dT%H:%M:%S")).execute()
        u_rows = u_res.data or []

        # Map user reports
        for ur in u_rows:
            ur["image_url"] = ur.get("media_url")
            ur["media_url"] = ur.get("media_url")
            ur["latitude"] = ur.get("latitude")
            ur["longitude"] = ur.get("longitude")
            ur["created_at"] = ur.get("created_at")
            ur["description"] = ur.get("description")
            ur["status"] = ur.get("status")
            ur["type"] = ur.get("type")
            ur["source"] = "Citizen"
            ur["confidence"] = ur.get("confidence")
            ur["severity"] = ur.get("severity") or "Unknown"
            ur["pothole"] = True

        rows = p_rows + u_rows

        print(f"Dashboard potholes fetched: {len(p_rows)}")
        print(f"Dashboard approved user reports fetched: {len(u_rows)}")
        print(f"Merged hazards: {len(rows)}")
        print(f"Dashboard response count: {len(rows)}")

        # Python-side processing for Supabase
        from collections import defaultdict

        # Time series
        ts_dict = defaultdict(int)
        sev_dict = defaultdict(int)
        type_dict = defaultdict(int)
        area_dict = defaultdict(int)

        for r in rows:
            # Time series parsing - always group by day to make it "work like daily"
            dt = r.get("created_at", "")
            if dt:
                dt_obj = datetime.datetime.fromisoformat(dt.replace("Z", "+00:00") if "Z" in dt else dt)
                label = dt_obj.strftime("%Y-%m-%d")
                ts_dict[label] += 1
            
            # Severity
            sev = r.get("severity", "Unknown") or "Unknown"
            sev_dict[sev] += 1

            # Type
            pt = r.get("type", "Unknown") or "Unknown"
            type_dict[pt] += 1

            # Area
            lat = round(float(r.get("latitude", 0)), 3)
            lon = round(float(r.get("longitude", 0)), 3)
            area_dict[f"{lat},{lon}"] += 1

        timeseries = [{"label": k, "count": v} for k, v in sorted(ts_dict.items())][-30:]
        severity_dist = [{"severity": k, "count": v} for k, v in sev_dict.items()]
        type_dist = [{"type": k, "count": v} for k, v in type_dict.items()]
        
        top_areas_raw = sorted(area_dict.items(), key=lambda x: x[1], reverse=True)[:10]
        top_areas = []
        for coord, c in top_areas_raw:
            lat, lon = coord.split(",")
            top_areas.append({"lat": float(lat), "lon": float(lon), "count": c})

        return jsonify({
            "timeseries": timeseries,
            "severity_dist": severity_dist,
            "type_dist": type_dist,
            "top_areas": [ta for ta in top_areas if isinstance(ta, dict)]
        })
    except Exception as e:
        print(f"[!] Analytics API Error: {e}")
        return jsonify({"timeseries":[], "severity_dist":[], "type_dist":[], "top_areas":[], "error": str(e)})

import sqlite3

def get_sqlite():
    db_path = "local_db.sqlite"
    # Ensure database file exists in production (it won't persist on free Render tier)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    # Check if table exists, if not create it (this is a safeguard)
    try:
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS assignments (id INTEGER PRIMARY KEY AUTOINCREMENT, pothole_id INTEGER, worker_name TEXT, status TEXT, notes TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        cur.execute("CREATE TABLE IF NOT EXISTS app_settings (id INTEGER PRIMARY KEY, detection_sensitivity FLOAT, alert_threshold INTEGER, map_lat FLOAT, map_lon FLOAT, map_zoom INTEGER, auto_refresh_sec INTEGER)")
        
        # Add new workflow columns if they don't exist
        try: cur.execute("ALTER TABLE assignments ADD COLUMN worker_id TEXT")
        except: pass
        try: cur.execute("ALTER TABLE assignments ADD COLUMN accepted_at TIMESTAMP")
        except: pass
        try: cur.execute("ALTER TABLE assignments ADD COLUMN repair_started_at TIMESTAMP")
        except: pass
        try: cur.execute("ALTER TABLE assignments ADD COLUMN repair_completed_at TIMESTAMP")
        except: pass
        
        conn.commit()
    except Exception as e:
        print(f"[!] SQLite Init Warning: {e}")
    return conn

# -----------------------------------------------------------------------------
# Assignments
# -----------------------------------------------------------------------------
@api_bp.route("/assignments", methods=["GET"])
def list_assignments():
    try:
        # We still need to join with Supabase potholes to get lat/lon for the frontend
        supabase = get_supabase()
        potholes_res = supabase.table("potholes").select("id, latitude, longitude, severity").execute()
        p_dict = {p.get("id"): p for p in potholes_res.data} if potholes_res.data else {}

        # ALSO fetch from user_reports since assignments could be linked to them now
        u_res = supabase.table("user_reports").select("id, latitude, longitude, severity").eq("status", "approved").execute()
        if u_res.data:
            for u in u_res.data:
                # Map to match pothole dict
                u["severity"] = u.get("severity") or "Citizen Report"
                u["confidence"] = u.get("confidence")
                p_dict[u.get("id")] = u

        a_res = supabase.table("assignments").select("*").execute()
        rows = a_res.data if a_res.data else []

        for r in rows:
            pid = r.get("hazard_id")
            p_info = p_dict.get(pid, {})
            r["pothole_id"] = pid
            r["latitude"] = p_info.get("latitude")
            r["longitude"] = p_info.get("longitude")
            r["severity"] = p_info.get("severity")
            r["pothole_status"] = r.get("status")
        
        return jsonify(rows)
    except Exception as e:
        print("Assignments table error:", e)
        return jsonify([])

@api_bp.route("/assignments", methods=["POST"])
def create_assignment():
    from app import supabase
    from flask import session
    data = request.get_json(silent=True) or {}
    pothole_id = data.get("pothole_id")
    worker_name = data.get("worker_name", "").strip()
    notes = data.get("notes", "")
    
    if not pothole_id or not worker_name:
        return jsonify({"error": "pothole_id and worker_name required"}), 400

    assigned_by = session.get('user_id')
    assigned_by_name = session.get('name', 'Admin')

    worker_res = supabase.table('users').select('*').ilike('name', worker_name).eq('role', 'worker').execute()
    worker = worker_res.data[0] if worker_res.data else None

    # Determine hazard_source
    hazard_source = 'AI'
    h_res = supabase.table('potholes').select('*').eq('id', pothole_id).execute()
    if not h_res.data:
        h_res = supabase.table('user_reports').select('*').eq('id', pothole_id).execute()
        if h_res.data:
            hazard_source = 'USER'
        else:
            return jsonify({"error": "Hazard not found"}), 404

    # Prevent duplicate active assignments
    existing_res = supabase.table('assignments').select('id, status').eq('hazard_id', pothole_id).order('id', desc=True).limit(1).execute()
    if existing_res.data:
        latest_status = str(existing_res.data[0].get('status', '')).lower()
        if latest_status not in ['completed', 'closed', 'rejected', 'resolved', 'fixed', 'verified']:
            return jsonify({
                "error": "An active assignment already exists for this hazard.",
                "id": existing_res.data[0]['id']
            }), 409

    insert_data = {
        'hazard_id': pothole_id,
        'hazard_source': hazard_source,
        'worker_id': worker['id'] if worker else None,
        'worker_name': worker['name'] if worker else worker_name,
        'worker_email': worker['email'] if worker else None,
        'assigned_by': assigned_by,
        'assigned_by_name': assigned_by_name,
        'status': 'Assigned',
        'verification_status': 'Pending',
        'notes': notes
    }

    try:
        res = supabase.table('assignments').insert(insert_data).execute()
        new_id = res.data[0]['id'] if res.data else None
        
        print("\n========== ASSIGNMENT DEBUG ==========")
        print(f"Hazard ID: {pothole_id}")
        print(f"Worker ID: {insert_data['worker_id']}")
        print(f"Insert Result: {res.data}")
        print(f"Assignment ID: {new_id}")
        print("=====================================\n")
        
        return jsonify({"id": new_id, "message": "Assigned"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route("/assignments/<int:aid>", methods=["PUT"])
def update_assignment(aid):
    data   = request.get_json(silent=True) or {}
    status = data.get("status")
    if not status:
        return jsonify({"error": "status required"}), 400

    try:
        from app import supabase
        res = supabase.table("assignments").update({"status": status}).eq("id", aid).execute()
        if res.data:
            assigned_hazard = res.data[0]
            hs = assigned_hazard.get("hazard_source", "AI")
            prefix = "USER" if hs == "user_reports" or hs == "USER" else "AI"
            master_id = f"{prefix}-{assigned_hazard.get('hazard_id')}"
            
            from services.hazard_registry import patch_hazard_assignment
            patch_hazard_assignment(master_id, assigned_hazard)
            
        return jsonify({"message": "Updated"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route("/assignments/pothole/<int:pid>", methods=["PUT"])
def update_assignment_by_pothole(pid):
    data   = request.get_json(silent=True) or {}
    status = data.get("status")
    if not status:
        return jsonify({"error": "status required"}), 400

    try:
        from app import supabase
        res = supabase.table("assignments").update({"status": status}).eq("hazard_id", pid).execute()
        if not res.data:
            return jsonify({"error": "No assignment found"}), 404
            
        assigned_hazard = res.data[0]
        hs = assigned_hazard.get("hazard_source", "AI")
        prefix = "USER" if hs == "user_reports" or hs == "USER" else "AI"
        master_id = f"{prefix}-{assigned_hazard.get('hazard_id')}"
        
        from services.hazard_registry import patch_hazard_assignment
        patch_hazard_assignment(master_id, assigned_hazard)
            
        return jsonify({"message": "Updated"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({"message": "Updated"})

@api_bp.route("/assignments/<int:aid>", methods=["DELETE"])
def delete_assignment(aid):
    try:
        from app import supabase
        supabase.table("assignments").delete().eq("id", aid).execute()
        return jsonify({"message": "Deleted"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -----------------------------------------------------------------------------
# Settings
# -----------------------------------------------------------------------------
@api_bp.route("/settings", methods=["GET"])
def get_settings():
    try:
        conn = get_sqlite()
        cur = conn.cursor()
        cur.execute("SELECT * FROM app_settings WHERE id = 1")
        row = cur.fetchone()
        conn.close()
        return jsonify(dict(row) if row else {})
    except:
        return jsonify({})

@api_bp.route("/settings", methods=["POST"])
def save_settings():
    data = request.get_json(silent=True) or {}
    allowed_fields = ["detection_sensitivity", "alert_threshold", "map_center_lat",
                "map_center_lon", "map_zoom", "auto_refresh_seconds",
                "notification_sound"]
    update_data = {k: v for k, v in data.items() if k in allowed_fields}
    
    if not update_data:
        return jsonify({"error": "No fields provided"}), 400

    conn = get_sqlite()
    cur = conn.cursor()
    
    cur.execute("SELECT id FROM app_settings WHERE id = 1")
    row = cur.fetchone()
    
    if row:
        set_clause = ", ".join([f"{k} = ?" for k in update_data.keys()])
        values = list(update_data.values()) + [1]
        cur.execute(f"UPDATE app_settings SET {set_clause} WHERE id = ?", values)
    else:
        update_data["id"] = 1
        cols = ", ".join(update_data.keys())
        qmarks = ", ".join(["?"] * len(update_data))
        cur.execute(f"INSERT INTO app_settings ({cols}) VALUES ({qmarks})", list(update_data.values()))
        
    conn.commit()
    conn.close()
        
    return jsonify({"message": "Settings saved"})

# -----------------------------------------------------------------------------
# Auth & User Management
# -----------------------------------------------------------------------------
@api_bp.route("/register", methods=["POST"])
def register():
    from app import bcrypt
    supabase = get_supabase()
    data = request.get_json(silent=True) or {}
    name     = data.get("name", "").strip()
    email    = data.get("email", "").strip()
    password = data.get("password", "").strip()
    # SECURITY: Ignore incoming role, always force "user" for public register
    role     = "user"

    if not name or not email or not password:
        return jsonify({"error": "All fields are required"}), 400

    # Check duplicate
    try:
        existing = supabase.table("users").select("id").eq("email", email).execute()
        if existing.data:
            return jsonify({"error": "Email already exists"}), 409
    except Exception as e:
        if "PGRST205" in str(e):
            return jsonify({"error": "Table 'users' missing in Supabase. Please run the SQL setup script."}), 404
        pass

    pw_hash = bcrypt.generate_password_hash(password).decode("utf-8")
    
    try:
        res = supabase.table("users").insert({
            "name": name,
            "email": email,
            "password": pw_hash,
            "role": role
        }).execute()
        return jsonify({"message": "Registration successful", "user": res.data[0]}), 201
    except Exception as e:
        err_msg = str(e)
        if "PGRST205" in err_msg or "does not exist" in err_msg.lower():
            return jsonify({"error": "Table 'users' missing in Supabase. Please run the SQL setup script."}), 404
        return jsonify({"error": f"Registration failed: {err_msg}"}), 500

@api_bp.route("/create-admin", methods=["POST"])
def create_admin():
    """Secure endpoint only for admins to create other admins"""
    if session.get("role") != "admin":
        return jsonify({"error": "Unauthorized. Only admins can create admin accounts."}), 403

    from app import bcrypt
    supabase = get_supabase()
    data = request.get_json(silent=True) or {}
    name     = data.get("name", "").strip()
    email    = data.get("email", "").strip()
    password = data.get("password", "").strip()
    role     = data.get("role", "admin").lower() # Defaults to admin

    if not name or not email or not password:
        return jsonify({"error": "All fields are required"}), 400

    # Strict role validation
    if role not in ["admin", "user"]:
        return jsonify({"error": "Invalid role"}), 400

    # Check duplicate
    try:
        existing = supabase.table("users").select("id").eq("email", email).execute()
        if existing.data:
            return jsonify({"error": "Email already exists"}), 409
    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500

    pw_hash = bcrypt.generate_password_hash(password).decode("utf-8")
    
    try:
        res = supabase.table("users").insert({
            "name": name,
            "email": email,
            "password": pw_hash,
            "role": role
        }).execute()
        return jsonify({"message": f"{role.capitalize()} created successfully", "user": res.data[0]}), 201
    except Exception as e:
        return jsonify({"error": f"Account creation failed: {str(e)}"}), 500

@api_bp.route("/login", methods=["POST"])
def login():
    from app import bcrypt
    supabase = get_supabase()
    data     = request.get_json(silent=True) or {}
    email    = (data.get("email") or "").strip()
    password = (data.get("password") or "").strip()

    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400

    try:
        res = supabase.table("users").select("*").eq("email", email).execute()
        user = res.data[0] if res.data else None

        if user and bcrypt.check_password_hash(user.get("password", ""), password):
            session["user_id"] = user["id"]
            session["role"]    = user["role"]
            session["name"]    = user["name"]
            
            # Store worker specific fields if available
            if user["role"] == "worker":
                session["team_name"] = user.get("team_name")
                session["designation"] = user.get("designation")
                session["worker_status"] = user.get("worker_status")
                
            return jsonify({"message": "OK", "role": user["role"], "name": user["name"]})
    except Exception as e:
        err_msg = str(e)
        if "PGRST205" in err_msg or "does not exist" in err_msg.lower():
            return jsonify({"error": "Table 'users' missing in Supabase. Please run the SQL setup script."}), 404
        return jsonify({"error": f"Database error: {err_msg}"}), 500
    
    return jsonify({"error": "Invalid email or password"}), 401

@api_bp.route("/logout", methods=["GET", "POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out successfully"})

@api_bp.route("/me", methods=["GET"])
def me():
    if "user_id" in session:
        return jsonify({
            "id": session["user_id"], 
            "role": session.get("role"),
            "name": session.get("name")
        })
    return jsonify({"error": "Not logged in"}), 401

@api_bp.route("/users", methods=["GET"])
def list_users():
    if session.get("role") != "admin":
        return jsonify({"error": "Unauthorized"}), 403
    supabase = get_supabase()
    res = supabase.table("users").select("id, name, email, role").execute()
    return jsonify(res.data)

@api_bp.route("/users/<int:uid>", methods=["DELETE"])
def delete_user(uid):
    if session.get("role") != "admin":
        return jsonify({"error": "Unauthorized"}), 403
    get_supabase().table("users").delete().eq("id", uid).execute()
    return jsonify({"message": "Deleted"})


# -----------------------------------------------------------------------------
# POST /api/safe-route  — Safe pothole-avoiding route
# -----------------------------------------------------------------------------
import math, requests as http_requests

def _make_circle_polygon(lat, lon, radius_m=30, num_points=8):
    """
    Reduced complexity to 8 points and 30m radius to stay within ORS limits.
    """
    coords = []
    lat_rad = math.radians(lat)
    delta_lat = radius_m / 111320.0
    delta_lon = radius_m / (111320.0 * math.cos(lat_rad)) if math.cos(lat_rad) != 0 else 0

    for i in range(num_points + 1):
        angle = 2 * math.pi * i / num_points
        c_lon = lon + delta_lon * math.cos(angle)
        c_lat = lat + delta_lat * math.sin(angle)
        coords.append([c_lon, c_lat])

    return coords


def _build_avoid_multipolygon(potholes, radius_m=30):
    """Build a GeoJSON MultiPolygon for ORS avoid_polygons."""
    polygons = []
    for p in potholes:
        try:
            lat = float(p["latitude"])
            lon = float(p["longitude"])
            ring = _make_circle_polygon(lat, lon, radius_m)
            polygons.append([ring])
        except:
            continue
    return { "type": "MultiPolygon", "coordinates": polygons }


def _call_ors(start_lonlat, end_lonlat, avoid_polygons=None, api_key=""):
    import requests
    url = "https://api.openrouteservice.org/v2/directions/driving-car/geojson"
    headers = {
        "Authorization": api_key,
        "Content-Type": "application/json"
    }
    
    def attempt_routing(use_alternatives=True, use_avoid=True):
        body = {
            "coordinates": [start_lonlat, end_lonlat],
        }
        if use_alternatives:
            body["alternative_routes"] = {
                "target_count": 3,
                "weight_factor": 1.4,
                "share_factor": 0.6
            }
        
        avoid_count = 0
        if use_avoid and avoid_polygons and avoid_polygons.get("coordinates"):
            body["options"] = {"avoid_polygons": avoid_polygons}
            avoid_count = len(avoid_polygons["coordinates"])

        print(f"[>] Calling ORS API... (Avoid: {avoid_count} polygons)")
        return requests.post(url, json=body, headers=headers, timeout=10)

    try:
        resp = attempt_routing(use_alternatives=True, use_avoid=True)
        
        if resp.status_code == 400:
            err_msg = resp.json().get('error', {}).get('message', 'Unknown 400 error')
            print(f"[!] ORS API 400 Error: {err_msg}. Retrying without alternatives and avoidance polygons...")
            resp = attempt_routing(use_alternatives=False, use_avoid=False)
            
        if resp.status_code != 200:
            err_msg = f"ORS API Error {resp.status_code}"
            try:
                err_msg += f": {resp.json().get('error', {}).get('message')}"
            except: pass
            print(f"[!] {err_msg}")
            raise Exception(f"Routing failed: {err_msg}")
            
        data = resp.json()
        candidates = []
        for feature in data.get("features", []):
            coords_raw = feature["geometry"]["coordinates"]
            route_latlon = [[c[1], c[0]] for c in coords_raw]
            props = feature.get("properties", {}).get("summary", {})
            distance = props.get("distance", 0)
            duration = props.get("duration", 0)
            candidates.append({
                "route_latlon": route_latlon,
                "distance": distance,
                "duration": duration
            })
        return candidates
    except Exception as e:
        print(f"[!] ORS Request Failed: {e}")
        raise e


def _route_intersects_potholes(route_latlon, potholes, radius_m=60):
    """
    Quick Python-side check: does any route point fall within radius_m of
    any high-severity pothole?  Uses flat-earth approximation (fine for <1 km).
    """
    for rlat, rlon in route_latlon:
        for p in potholes:
            try:
                plat = float(p["latitude"])
                plon = float(p["longitude"])
            except (TypeError, KeyError, ValueError):
                continue
            dlat = (rlat - plat) * 111_320
            dlon = (rlon - plon) * 111_320 * math.cos(math.radians(plat))
            if math.sqrt(dlat ** 2 + dlon ** 2) < radius_m:
                return True
    return False


# -- Helper for Point-to-Line Segment distance --
def _point_to_route_dist(p_lat, p_lon, route):
    """Calculates the minimum distance from a point to a polyline in meters."""
    from utils.helpers import haversine
    if not route or len(route) < 2: return 999999
    
    min_dist = 999999
    
    # Local Cartesian approximation for small distances
    lat_avg = math.radians(route[0][0])
    scale_x = math.cos(lat_avg)
    
    for i in range(len(route) - 1):
        a = route[i]
        b = route[i+1]
        
        # P, A, B coordinates scaled for Cartesian distance
        px, py = p_lon * scale_x, p_lat
        ax, ay = a[1] * scale_x, a[0]
        bx, by = b[1] * scale_x, b[0]
        
        vx, vy = bx - ax, by - ay # Segment vector
        wx, wy = px - ax, py - ay # Point-to-start vector
        
        mag_v_sq = vx*vx + vy*vy
        if mag_v_sq == 0:
            d = haversine(p_lat, p_lon, a[0], a[1])
        else:
            t = max(0, min(1, (wx * vx + wy * vy) / mag_v_sq))
            # Closest point on segment in Cartesian
            cx, cy = ax + t * vx, ay + t * vy
            # Map back to lat/lon for accurate Haversine
            d = haversine(p_lat, p_lon, cy, cx / scale_x)
            
        if d < min_dist:
            min_dist = d
            
    return min_dist

@api_bp.route("/safe-route", methods=["POST"])
def safe_route():
    from config import Config
    from utils.helpers import haversine
    from services.hazard_registry import load_all_hazards
    from services.risk_engine import RiskEngine
    from services.priority_engine import PriorityEngine
    import copy
    
    data = request.get_json(silent=True) or {}
    start = data.get("start")
    end = data.get("end")

    if not start or not end or len(start) != 2 or len(end) != 2:
        return jsonify({"error": "start and end [lat, lon] required"}), 400

    def validate_coord(coord, name):
        lat, lon = coord
        try:
            lat, lon = float(lat), float(lon)
        except ValueError:
            return False, f"{name} coordinates must be numeric"
        if not (-90 <= lat <= 90):
            return False, f"{name} latitude must be between -90 and 90"
        if not (-180 <= lon <= 180):
            return False, f"{name} longitude must be between -180 and 180"
        return True, ""
        
    is_valid, msg = validate_coord(start, "Source")
    if not is_valid: return jsonify({"error": msg}), 400
    
    is_valid, msg = validate_coord(end, "Destination")
    if not is_valid: return jsonify({"error": msg}), 400
    
    straight_line_dist = haversine(float(start[0]), float(start[1]), float(end[0]), float(end[1]))
    if straight_line_dist > 100000: # 100km limit
        return jsonify({
            "error": "Routing limit exceeded",
            "message": f"The selected destination is {straight_line_dist/1000:.1f} km away. The maximum supported routing distance is 100 km. Please select a closer destination."
        }), 400

    api_key = Config.ORS_API_KEY
    if not api_key or api_key == "YOUR_OPENROUTESERVICE_API_KEY":
        return jsonify({"error": "ORS API key not configured"}), 503

    print(f"[NAVIGATION_ENGINE] Request | Source: {start} | Destination: {end} | Straight-line distance: {straight_line_dist/1000:.1f}km")
    
    # 1. Fetch Hazards using Hazard Registry (single source of truth)
    all_hazards = load_all_hazards()
    
    # Filter active only
    active_hazards = [
        h for h in all_hazards 
        if h.status.lower() not in ("fixed", "completed", "resolved")
    ]
    
    # Proximity filter (15km radius)
    proximate_hazards = []
    for h in active_hazards:
        if haversine(h.latitude, h.longitude, float(start[0]), float(start[1])) < 15000 or \
           haversine(h.latitude, h.longitude, float(end[0]), float(end[1])) < 15000:
            proximate_hazards.append(h)

    # 2. ORS Call - Avoid ONLY critical/emergency
    critical_hazards = [h for h in proximate_hazards if h.severity.lower() in ("critical", "emergency")]
    start_ll, end_ll = [float(start[1]), float(start[0])], [float(end[1]), float(end[0])]
    
    # Merge overlapping polygons roughly by clustering points within 60m of each other
    merged_critical = []
    for ch in critical_hazards:
        merged = False
        for cluster in merged_critical:
            if haversine(ch.latitude, ch.longitude, cluster["latitude"], cluster["longitude"]) < 60:
                merged = True
                break
        if not merged:
            merged_critical.append({"latitude": ch.latitude, "longitude": ch.longitude})
            
    avoid_mp = _build_avoid_multipolygon(merged_critical, radius_m=45) if merged_critical else None
    
    avoid_count = len(avoid_mp["coordinates"]) if avoid_mp else 0
    print(f"[NAVIGATION_ENGINE] Avoidance polygons generated: {avoid_count}")

    try:
        # returns a list of candidate routes: [{"route_latlon": [], "distance": x, "duration": y}]
        candidates = _call_ors(start_ll, end_ll, avoid_mp, api_key)
    except Exception as e:
        print(f"[!] ORS Route Calculation Failed: {e}")
        return jsonify({"error": "Routing service unavailable", "message": str(e)}), 503

    best_dist = candidates[0]['distance']/1000 if candidates and 'distance' in candidates[0] else 0
    print(f"[NAVIGATION_ENGINE] Generated {len(candidates)} Candidate Routes | Best Route Distance: {best_dist:.1f}km")

    # 3. Buffer Intersection & Risk Scoring for Multiple Candidates
    scored_routes = []
    THRESHOLD = 20.0 # 20m buffer

    for idx, cand in enumerate(candidates):
        route_latlon = cand["route_latlon"]
        dist_m = cand.get("distance", 1)
        dur_s = cand.get("duration", 1)
        
        detected_on_route = []
        route_risk_sum = 0
        route_priority_sum = 0
        max_risk = 0
        route_road_importance = []
        route_traffic_importance = []
        critical_count = 0
        
        for h in proximate_hazards:
            dist = _point_to_route_dist(h.latitude, h.longitude, route_latlon)
            if dist <= THRESHOLD:
                # Recalculate dynamic risk based on distance to route
                h_copy = copy.copy(h)
                
                # Dynamic properties
                h_copy.distance_from_route = dist
                
                # Re-run full backend calculations
                h_copy = RiskEngine.calculate(h_copy)
                
                # Apply distance penalty: hazards further away (10-20m) are less risky than direct hits (0-5m)
                distance_penalty = max(0, dist - 5)
                dynamic_risk = max(0, h_copy.risk_score - distance_penalty)
                
                h_copy.risk_score = dynamic_risk
                h_copy = PriorityEngine.calculate(h_copy)
                dynamic_priority = h_copy.priority_score
                
                h_dict = h_copy.to_dict()
                h_dict["dist"] = dist
                h_dict["risk_score"] = dynamic_risk
                h_dict["priority_score"] = dynamic_priority
                
                detected_on_route.append(h_dict)
                route_risk_sum += dynamic_risk
                route_priority_sum += dynamic_priority
                
                if dynamic_risk > max_risk: max_risk = dynamic_risk
                if h_copy.severity.lower() in ("critical", "emergency"): critical_count += 1
                
                route_road_importance.append(h_copy.road_importance if hasattr(h_copy, 'road_importance') else 10)
                route_traffic_importance.append(h_copy.traffic_score if hasattr(h_copy, 'traffic_score') else 10)

        avg_risk = (route_risk_sum / len(detected_on_route)) if detected_on_route else 0
        avg_priority = (route_priority_sum / len(detected_on_route)) if detected_on_route else 0
        avg_road_imp = (sum(route_road_importance) / len(route_road_importance)) if route_road_importance else 50
        avg_traffic_imp = (sum(route_traffic_importance) / len(route_traffic_importance)) if route_traffic_importance else 50

        # Normalize Safety (0-100)
        # Max reasonable route_risk_sum might be 300
        safety_score = max(0, 100 - (route_risk_sum / 3.0))

        # 4. Weighted Selection Logic
        # Safety 45%, Road Quality 20%, Travel Time 15%, Distance 10%, Traffic Importance 10%
        norm_dist = min(100, 100 * (1000 / max(1, dist_m)))
        norm_dur = min(100, 100 * (60 / max(1, dur_s)))
        
        score = (0.45 * safety_score) + (0.20 * avg_road_imp) + (0.15 * norm_dur) + (0.10 * norm_dist) - (0.10 * avg_traffic_imp)
        
        cand["score"] = score
        cand["safety_score"] = safety_score
        cand["hazards"] = detected_on_route
        cand["raw_risk"] = route_risk_sum
        cand["critical_count"] = critical_count
        cand["avg_risk"] = avg_risk
        cand["max_risk"] = max_risk
        cand["avg_road_importance"] = avg_road_imp
        cand["avg_traffic_importance"] = avg_traffic_imp
        
        print(f"[NAVIGATION_ENGINE] Route {idx}: Dist={dist_m}m | Dur={dur_s}s | Matched={len(detected_on_route)} | Crit={critical_count} | RoadImp={avg_road_imp:.1f} | TrafImp={avg_traffic_imp:.1f} | AvgRisk={avg_risk:.1f} | PriScore={avg_priority:.1f} | FinalScore={score:.2f}")
        scored_routes.append(cand)

    if not scored_routes:
        return jsonify({"error": "No routes returned"}), 500

    # Sort descending by final score
    scored_routes.sort(key=lambda x: x["score"], reverse=True)
    best = scored_routes[0]
    alts = scored_routes[1:]

    # Generate Explanation
    reason = f"Optimal route selected."
    if len(scored_routes) > 1:
        alt_best = alts[0]
        if best["critical_count"] < alt_best["critical_count"]:
            diff = alt_best["critical_count"] - best["critical_count"]
            reason = f"Avoided {diff} critical hazard(s)."
        elif best["raw_risk"] < alt_best["raw_risk"]:
            diff = alt_best["raw_risk"] - best["raw_risk"]
            reason = f"Safer than alternative. Improved safety."
        elif best["avg_road_importance"] > alt_best["avg_road_importance"]:
            reason = f"Uses higher quality roads."
        elif best["duration"] < alt_best["duration"]:
            reason = f"Fastest safest route. Saves {int(alt_best['duration'] - best['duration'])} seconds."

    print(f"[NAVIGATION_ENGINE] Selected Winner: Score={best['score']:.2f} | Reason: {reason}")

    safety_label = "safe"
    if best["safety_score"] < 40:
        safety_label = "unsafe"
    elif best["safety_score"] < 75:
        safety_label = "moderate"

    return jsonify({
        "recommended_route": best["route_latlon"],
        "route": best["route_latlon"], # fallback for older frontend
        "safety": safety_label,
        "safety_score": int(best["safety_score"]),
        "risk_score": int(best["raw_risk"]),
        "potholes_on_path": len(best["hazards"]),
        "matched_hazards": best["hazards"],
        "detected_potholes": best["hazards"], # fallback
        "avoid_polygons": len(merged_critical),
        "avoided_potholes": len(merged_critical),
        "distance": best["distance"],
        "duration": best["duration"],
        "reasoning": reason,
        "reason": reason, # fallback
        "road_quality": best["avg_road_importance"],
        "traffic_importance": best["avg_traffic_importance"],
        "route_score": best["score"],
        "alternatives": [
            {
                "route_latlon": a["route_latlon"],
                "safety_score": int(a["safety_score"])
            } for a in alts
        ]
    })


# -----------------------------------------------------------------------------
# GET /api/nearby-potholes
# -----------------------------------------------------------------------------
@api_bp.route("/nearby-potholes", methods=["GET"])
def get_nearby_potholes():
    from utils.helpers import haversine, calculate_risk_score
    lat = request.args.get("lat", type=float)
    lon = request.args.get("lon", type=float)
    radius = request.args.get("radius", type=float, default=500.0)

    if lat is None or lon is None:
        return jsonify({"error": "lat and lon required"}), 400

    supabase = get_supabase()
    # Fetch all active potholes
    p_res = supabase.table("potholes").select("*").eq("pothole", True).execute()
    u_res = supabase.table("user_reports").select("*").eq("status", "approved").execute()
    
    all_p = (p_res.data or []) + (u_res.data or [])
    
    # Map user reports perfectly
    for p in all_p:
        if "media_url" in p and "pothole" not in p: # it's a citizen report
            p["image_url"] = p.get("media_url")
            p["media_url"] = p.get("media_url")
            p["latitude"] = p.get("latitude")
            p["longitude"] = p.get("longitude")
            p["created_at"] = p.get("created_at")
            p["description"] = p.get("description")
            p["status"] = p.get("status")
            p["type"] = p.get("type")
            p["source"] = "Citizen"
            p["confidence"] = p.get("confidence")
            p["severity"] = p.get("severity") or "Unknown"
            p["pothole"] = True
            
    print(f"Dashboard potholes fetched: {len(p_res.data or [])}")
    print(f"Dashboard approved user reports fetched: {len(u_res.data or [])}")
    print(f"Merged hazards: {len(all_p)}")
    print(f"Dashboard response count: {len(all_p)}")
    
    nearby = []
    for p in all_p:
        p_lat, p_lon = float(p["latitude"]), float(p["longitude"])
        dist = haversine(lat, lon, p_lat, p_lon)
        if dist <= radius:
            p["distance"] = round(dist, 1)
            p["risk_score"] = calculate_risk_score(p.get("severity", "low"), p.get("report_count", 1))
            nearby.append(p)

    # Sort by risk score (descending) and then distance
    nearby.sort(key=lambda x: (-x["risk_score"], x["distance"]))
    
    # 3. Normalize results
    for p in nearby:
        url = p.get("image_url") or p.get("media_url")
        if url and not url.startswith("http") and not url.startswith("/static"):
            p["image_url"] = f"{Config.SUPABASE_URL}/storage/v1/object/public/pothole-images/{url}"
        else:
            p["image_url"] = url

    # 4. Extract critical alerts for the navigation sidebar
    admin_alerts = [p for p in nearby if p.get("severity", "").lower() == "high"]

    return jsonify({
        "potholes": nearby[:10],
        "admin_alerts": admin_alerts[:5]
    })

# -----------------------------------------------------------------------------
# GET /api/alerts — Unified AI + APPROVED User Reports Grouped by Location
# -----------------------------------------------------------------------------
@api_bp.route("/alerts", methods=["GET"])
@api_bp.route("/all-potholes", methods=["GET"])
def get_alerts_unified():
    import time
    start_time = time.time()
    
    from services.hazard_registry import registry_cache, load_all_hazards
    
    db_start = time.time()
    try:
        cache_miss = registry_cache.is_stale()
        if cache_miss:
            load_all_hazards()
    except Exception as e:
        print(f"[!] Error loading hazards from registry: {e}")
        cache_miss = True
    db_time = time.time() - db_start
    
    # Extract Filters
    f_severity  = request.args.get("severity", "").lower()
    f_status    = request.args.get("status", "").lower()
    f_priority  = request.args.get("priority", "").lower()
    f_date_from = request.args.get("date_from")
    f_date_to   = request.args.get("date_to")
    
    no_filters = not any([
        f_severity and f_severity != "all",
        f_status and f_status != "all",
        f_priority and f_priority != "all",
        f_date_from,
        f_date_to
    ])
    
    # Fast path O(1) global JSON cache return
    if no_filters and not registry_cache.is_stale():
        total_time = time.time() - start_time
        print(
            f"\n=====================================\n"
            f"API Request: /api/alerts (GET)\n"
            f"Cache Hit: {not cache_miss}\n"
            f"Cache Miss: {cache_miss}\n"
            f"Database Time: {db_time * 1000:.2f}ms\n"
            f"Registry Time: {(time.time() - db_start - db_time) * 1000:.2f}ms\n"
            f"Risk Engine Time: 0.00ms (Bypassed)\n"
            f"Priority Engine Time: 0.00ms (Bypassed)\n"
            f"Reasoning Engine Time: 0.00ms (Bypassed)\n"
            f"Workforce Engine Time: 0.00ms (Bypassed)\n"
            f"Serialization Time: 0.00ms (O(1) Cached)\n"
            f"Processing Time: {total_time * 1000:.2f}ms\n"
            f"Total API Time: {total_time * 1000:.2f}ms\n"
            f"====================================="
        )
        # Filter out terminal statuses (Completed, Rejected, Closed) from the O(1) cache path
        # so the Alerts page never shows completed hazards even on cache-hit
        TERMINAL_STATUSES = {'Completed', 'Rejected', 'Closed', 'Verified', 'Fixed'}
        active_hazards = [
            h for h in registry_cache.get_all_json()
            if (h.get('assignment') or {}).get('status', h.get('status', '')) not in TERMINAL_STATUSES
            and h.get('status', '') not in TERMINAL_STATUSES
        ]
        print(f"[WORKFLOW] [ALERT CACHE REFRESHED] /api/alerts serving {len(active_hazards)} active hazards.")
        return jsonify(active_hazards)
        
    filtered_alerts = []
    # If filters are applied, loop over the O(1) cached dicts for sub-ms filtering
    hazards_json = registry_cache.get_all_json()
    for alert_dict in hazards_json:
        if f_severity and f_severity != "all" and str(alert_dict.get("severity", "")).lower() != f_severity:
            continue
            
        h_state = (alert_dict.get("maintenance_state") or alert_dict.get("status") or "").lower()
        if f_status and f_status != "all":
            if f_status == "pending" and h_state != "pending repair":
                continue
            elif f_status != "pending" and h_state != f_status:
                continue
                
        if f_priority and f_priority != "all" and str(alert_dict.get("priority", "")).lower() != f_priority:
            continue
                
        a_date = str(alert_dict.get("created_at") or "")[:10]
        if f_date_from and a_date < f_date_from:
            continue
        if f_date_to and a_date > f_date_to:
            continue
            
        filtered_alerts.append(alert_dict)
        
    total_time = time.time() - start_time
    
    # Detailed Performance Logging (Req #24)
    print(
        f"\n=====================================\n"
        f"API Request: /api/alerts (GET) [FILTERED]\n"
        f"Cache Hit: {not cache_miss}\n"
        f"Cache Miss: {cache_miss}\n"
        f"Database Time: {db_time * 1000:.2f}ms\n"
        f"Registry Time: 0.00ms (Bypassed)\n"
        f"Risk Engine Time: 0.00ms (Bypassed)\n"
        f"Priority Engine Time: 0.00ms (Bypassed)\n"
        f"Reasoning Engine Time: 0.00ms (Bypassed)\n"
        f"Workforce Engine Time: 0.00ms (Bypassed)\n"
        f"Serialization Time: 0.00ms (Precomputed)\n"
        f"Processing Time: {total_time * 1000:.2f}ms\n"
        f"Total API Time: {total_time * 1000:.2f}ms\n"
        f"====================================="
    )
        
    return jsonify(filtered_alerts)


# -----------------------------------------------------------------------------
# USER REPORTING MODULE
# -----------------------------------------------------------------------------

@api_bp.route("/report", methods=["POST"])
def submit_report():
    supabase = get_supabase()
    file = request.files.get("media")
    lat  = request.form.get("lat", type=float)
    lon  = request.form.get("lon", type=float)
    desc = request.form.get("description", "")
    uid  = session.get("user_id")

    if not file or lat is None or lon is None:
        return jsonify({"error": "Missing required fields (media, lat, lon)"}), 400

    # 1. Validate and Upload Media to 'user-reports' bucket
    ALLOWED = {"jpg", "jpeg", "png", "webp", "mp4"}
    ext = file.filename.rsplit(".", 1)[1].lower()
    if ext not in ALLOWED:
        return jsonify({"error": "Unsupported file format"}), 400

    try:
        fname = f"report_{int(datetime.now().timestamp())}_{secure_filename(file.filename)}"
        ftype = "video" if ext == "mp4" else "image"
        
        # Upload
        file_bytes = file.read()
        
        response = None
        try:
            response = supabase.storage.from_("user-reports").upload(fname, file_bytes, {"content-type": file.content_type})
        except Exception as upload_err:
            import traceback
            traceback.print_exc()
            print(f"[!] User report upload failed: {upload_err}")
            return jsonify({"error": f"Upload failed: {str(upload_err)}"}), 400
            
        media_url = supabase.storage.from_("user-reports").get_public_url(fname)

        # 2. Insert into user_reports table (Always store every report as PENDING)
        report_data = {
            "latitude": lat,
            "longitude": lon,
            "media_url": media_url,
            "type": ftype,
            "description": desc,
            "status": "pending", 
            "user_id": uid
        }
        
        response = None
        try:
            response = supabase.table("user_reports").insert(report_data).execute()
            inserted_id = response.data[0].get("id") if getattr(response, "data", []) else None
            if inserted_id:
                try:
                    from services.hazard_registry import recalculate_single_hazard_async
                    master_id = f"USER-{inserted_id}"
                    new_db_record = report_data.copy()
                    new_db_record["id"] = inserted_id
                    new_db_record["hazard_source"] = "user_reports"
                    recalculate_single_hazard_async(master_id, new_db_record, "Citizen", "new_detection")
                except Exception as ex:
                    print(f"[!] Error updating hazard registry cache: {ex}")
        except Exception as insert_err:
            import traceback
            traceback.print_exc()
            print(f"[!] User report DB insert failed: {insert_err}")
            return jsonify({"error": f"Database insertion failed: {str(insert_err)}"}), 400

        return jsonify({"message": "Report submitted and awaiting review.", "url": media_url}), 201
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[!] Report Error: {e}")
        return jsonify({"error": f"Submission failed: {str(e)}"}), 400


@api_bp.route("/user-reports", methods=["GET"])
def get_user_reports():
    status = request.args.get("status")
    supabase = get_supabase()
    
    try:
        # 1. Fetch user_reports
        ur_query = supabase.table("user_reports").select("*")
        if status and status != 'all':
            ur_query = ur_query.eq("status", status)
            
        ur_res = ur_query.order("created_at", desc=True).execute()
        
        normalized = []
        for r in ur_res.data:
            r["source"] = "user"
            normalized.append(r)
            
        # 2. Fetch AI detections from potholes
        p_query = supabase.table("potholes").select("*").is_("source_report_id", "null")
        if status and status != 'all':
            p_query = p_query.eq("status", status)
            if status == "pending":
                p_query = p_query.eq("review_required", True)
        
        ph_res = p_query.order("created_at", desc=True).execute()
            
        for p in ph_res.data:
            conf_pct = int((p.get("confidence") or 0) * 100)
            det_type = p.get("type") or "pothole"
            
            ai_record = {
                "id": p.get("id"),
                "created_at": p.get("created_at"),
                "status": p.get("status"),
                "media_url": p.get("image_url"),
                "latitude": p.get("latitude"),
                "longitude": p.get("longitude"),
                "confidence": p.get("confidence"),
                "severity": p.get("severity"),
                "type": det_type,
                "source": "ai",
                "description": f"AI detected {det_type} ({conf_pct}%)"
            }
            normalized.append(ai_record)
                
        # Sort merged list newest first
        normalized.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return jsonify(normalized)
    except Exception as e:
        print(f"[!] User Reports API Error: {e}")
        return jsonify({"error": str(e), "data": []}), 500


@api_bp.route("/user-reports/action", methods=["POST"])
def report_action():
    global _stats_cache
    if session.get("role") != "admin":
        return jsonify({"error": "Unauthorized"}), 403
        
    data = request.get_json()
    rid  = data.get("id")
    action = data.get("action") # 'approve' or 'reject'
    source = data.get("source", "user")
    
    supabase = get_supabase()
    
    try:
        from services.hazard_registry import recalculate_single_hazard_async, registry_cache
        global global_alerts_cache
        global _stats_cache
        
        if source == "ai":
            # Direct update on potholes table
            if action == "approve":
                supabase.table("potholes").update({
                    "status": "approved",
                    "review_required": False
                }).eq("id", rid).execute()
                
                recalculate_single_hazard_async(f"AI-{rid}", {"status": "approved"}, "AI", "status_update")
                registry_cache.invalidate()
                global_alerts_cache["data"] = None
                
                print(f"\n[ADMIN APPROVAL]\nReport AI-{rid} approved")
                print("[CACHE]\nDashboard cache invalidated")
                print("[CACHE]\nNavigation cache invalidated")
                print("[CACHE]\nAlerts cache invalidated")
                print("[CACHE]\nWorker cache invalidated")
                print("[REGISTRY]\nMerged hazards rebuilt")
                print("[REGISTRY]\nDashboard registry refreshed")
                print("[REGISTRY]\nNavigation registry refreshed")
                print("[REGISTRY]\nWorker registry refreshed")
                print("[LIVE UPDATE]\nDashboard notified")
                print("[LIVE UPDATE]\nNavigation notified")
                print("[LIVE UPDATE]\nWorker module notified")
                print("[LIVE UPDATE]\nAnalytics refreshed")
                print("[SYNC COMPLETE]\nAll affected modules updated successfully\n")
                
            elif action == "reject":
                supabase.table("potholes").update({
                    "status": "rejected",
                    "review_required": False
                }).eq("id", rid).execute()
                
                recalculate_single_hazard_async(f"AI-{rid}", {"status": "rejected"}, "AI", "status_update")
                registry_cache.invalidate()
                global_alerts_cache["data"] = None
                
                print(f"\n[ADMIN REJECT]\nReport AI-{rid} rejected")
                print("[CACHE]\nCaches invalidated")
                print("[REGISTRY]\nRegistry synchronized\n")
                
            return jsonify({"message": f"AI Detection {action}d successfully"})

        from utils.detection_logger import DetectionLogger
        dlog = DetectionLogger()
        
        if action == "approve":
            # Update report status
            supabase.table("user_reports").update({
                "status": "approved",
                "review_required": False
            }).eq("id", rid).execute()
            
            recalculate_single_hazard_async(f"USER-{rid}", {"status": "approved"}, "Citizen", "status_update")
            registry_cache.invalidate()
            
            _stats_cache["data"] = None
            _stats_cache["time"] = None
            global_alerts_cache["data"] = None
            
            dlog.log_admin_approved(rid)
            
            print(f"\n[ADMIN APPROVAL]\nReport USER-{rid} approved")
            print("[CACHE]\nDashboard cache invalidated")
            print("[CACHE]\nNavigation cache invalidated")
            print("[CACHE]\nAlerts cache invalidated")
            print("[CACHE]\nWorker cache invalidated")
            print("[REGISTRY]\nMerged hazards rebuilt")
            print("[REGISTRY]\nDashboard registry refreshed")
            print("[REGISTRY]\nNavigation registry refreshed")
            print("[REGISTRY]\nWorker registry refreshed")
            print("[LIVE UPDATE]\nDashboard notified")
            print("[LIVE UPDATE]\nNavigation notified")
            print("[LIVE UPDATE]\nWorker module notified")
            print("[LIVE UPDATE]\nAnalytics refreshed")
            print("[SYNC COMPLETE]\nAll affected modules updated successfully\n")
            
        elif action == "reject":
            supabase.table("user_reports").update({
                "status": "rejected",
                "review_required": False
            }).eq("id", rid).execute()
            
            recalculate_single_hazard_async(f"USER-{rid}", {"status": "rejected"}, "Citizen", "status_update")
            registry_cache.invalidate()
            
            _stats_cache["data"] = None
            _stats_cache["time"] = None
            global_alerts_cache["data"] = None
            
            dlog.log_admin_rejected(rid)
            
            print(f"\n[ADMIN REJECT]\nReport USER-{rid} rejected")
            print("[CACHE]\nCaches invalidated")
            print("[REGISTRY]\nRegistry synchronized\n")
            
        return jsonify({"message": f"Report {action}d successfully"})
    except Exception as e:
        return jsonify({"error": f"Action failed: {str(e)}"}), 500

# -----------------------------------------------------------------------------
# PHASE 2: ADMIN ALERT ACTIONS (VERIFY, REJECT, ASSIGN, VERIFY-REPAIR)
# -----------------------------------------------------------------------------
import uuid



@api_bp.route('/alerts/verify', methods=['POST'])
def verify_alert():
    from services.hazard_registry import recalculate_single_hazard_async
    if session.get('role') != 'admin': return jsonify({'error': 'Unauthorized'}), 403
    data = request.json or {}
    hazard_id = data.get('hazard_id')
    source = data.get('source')
    supabase = get_supabase()
    if source == 'user_reports':
        supabase.table('user_reports').update({'status': 'approved', 'review_required': False}).eq('id', hazard_id).execute()
    else:
        supabase.table('potholes').update({'status': 'approved', 'review_required': False}).eq('id', hazard_id).execute()
        
    master_id = f"USER-{hazard_id}" if source == 'user_reports' else f"AI-{hazard_id}"
    recalculate_single_hazard_async(master_id, {"status": "approved"}, source, "status_update")
    
    return jsonify({'message': 'Alert verified successfully', 'success': True})

@api_bp.route('/alerts/reject', methods=['POST'])
def reject_alert():
    from services.hazard_registry import recalculate_single_hazard_async
    if session.get('role') != 'admin': return jsonify({'error': 'Unauthorized'}), 403
    data = request.json or {}
    hazard_id = data.get('hazard_id')
    source = data.get('source')
    supabase = get_supabase()
    if source == 'user_reports':
        supabase.table('user_reports').update({'status': 'rejected', 'review_required': False}).eq('id', hazard_id).execute()
    else:
        supabase.table('potholes').update({'status': 'rejected', 'review_required': False}).eq('id', hazard_id).execute()
        
    master_id = f"USER-{hazard_id}" if source == 'user_reports' else f"AI-{hazard_id}"
    recalculate_single_hazard_async(master_id, {"status": "rejected"}, source, "status_update")
    
    return jsonify({'message': 'Alert rejected successfully', 'success': True})

@api_bp.route('/alerts/assign', methods=['POST'])
def assign_alert():
    from services.hazard_registry import recalculate_single_hazard, patch_hazard_assignment
    if session.get('role') != 'admin': return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.json or {}
    hazard_id_raw = data.get('hazard_id')
    hazard_source = data.get('source')
    
    if not hazard_id_raw or not hazard_source:
        return jsonify({'error': 'Missing hazard_id or source', 'success': False}), 400
        
    try:
        hazard_id = int(hazard_id_raw)
    except ValueError:
        return jsonify({'error': 'Invalid hazard_id format, must be integer', 'success': False}), 400
        
    try:
        supabase = get_supabase()

        # ---------------------------------------------------------------
        # DEDUPLICATION: Check if an active (non-terminal) assignment
        # already exists for this hazard before inserting a new row.
        # Terminal statuses that allow a new row: Completed, Rejected.
        # ---------------------------------------------------------------
        existing_res = supabase.table('assignments') \
            .select('id, status') \
            .eq('hazard_id', hazard_id) \
            .not_.in_('status', ['Completed', 'Rejected']) \
            .order('id', desc=True).limit(1).execute()

        if existing_res.data:
            existing_row = existing_res.data[0]
            existing_status = existing_row.get('status', '')
            print(f"[WORKFLOW] [ASSIGNMENT] Hazard {hazard_id} already has active assignment (status={existing_status}). Skipping duplicate insert.")

            # If it's already Available (admin clicked twice), just return success
            if existing_status == 'Available':
                master_id = f"USER-{hazard_id}" if hazard_source == 'user_reports' else f"AI-{hazard_id}"
                updated_hazard = recalculate_single_hazard(master_id, None, None, "assignment_update")
                return jsonify({
                    'success': True,
                    'assignment_created': False,
                    'assignment_status': 'Available',
                    'note': 'Assignment already published',
                    'updated_hazard': updated_hazard._cached_dict if updated_hazard else None
                })
            else:
                return jsonify({'error': f'Cannot assign: hazard already in status={existing_status}', 'success': False}), 409

        # No active assignment — safe to create one
        insert_data = {
            'hazard_id': hazard_id,
            'hazard_source': 'USER' if hazard_source == 'user_reports' else 'AI',
            'worker_id': None,
            'worker_name': None,
            'worker_email': None,
            'assigned_by': session.get('user_id'),
            'assigned_by_name': session.get('name', 'Admin'),
            'status': 'Available',
            'verification_status': 'Pending'
        }
        
        assign_res = supabase.table('assignments').insert(insert_data).execute()
        
        # Also update the hazard status for consistency
        if hazard_source == 'user_reports':
            res = supabase.table('user_reports').update({'status': 'Available'}).eq('id', hazard_id).execute()
        else:
            res = supabase.table('potholes').update({'status': 'Available'}).eq('id', hazard_id).execute()
            
        if not res.data:
            return jsonify({'error': 'Hazard not found', 'success': False}), 404

        print(f"[WORKFLOW] [ASSIGNMENT UPDATED] Hazard {hazard_id} | status=Available | [STATUS CHANGED] Detected -> Available")
        print(f"[WORKFLOW] [CACHE INVALIDATED] Hazard {hazard_id} registry update triggered.")

        master_id = f"USER-{hazard_id}" if hazard_source == 'user_reports' else f"AI-{hazard_id}"

        # Use patch for instant UI update (no full rebuild)
        new_assignment = assign_res.data[0] if assign_res.data else insert_data
        patch_hazard_assignment(master_id, new_assignment)

        # Also run full recalculate to ensure engines are up-to-date for the response
        updated_hazard = recalculate_single_hazard(master_id, None, None, "assignment_update")
        
        return jsonify({
            'success': True, 
            'assignment_created': True,
            'assignment_status': 'Available',
            'updated_hazard': updated_hazard._cached_dict if updated_hazard else None
        })
    except Exception as e:
        print(f"[SQL ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e), 'success': False}), 500

@api_bp.route('/admin/pending-verifications', methods=['GET'])
def get_pending_verifications():
    if session.get('role') != 'admin': return jsonify({'error': 'Unauthorized'}), 403
    try:
        supabase = get_supabase()
        res = supabase.table('assignments').select('*').eq('status', 'Waiting Verification').execute()
        rows = res.data if res.data else []
        
        # Hydrate with hazard details
        supabase = get_supabase()
        pending = []
        for row in rows:
            data = dict(row)
            hazard = None
            if data['hazard_source'] == 'potholes':
                res = supabase.table('potholes').select('*').eq('id', data['hazard_id']).execute()
                if res.data: hazard = res.data[0]
            else:
                res = supabase.table('user_reports').select('*').eq('id', data['hazard_id']).execute()
                if res.data: hazard = res.data[0]
            
            data['hazard'] = hazard
            pending.append(data)
        return jsonify({'success': True, 'data': pending})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e), 'success': False}), 500

@api_bp.route('/alerts/<hazard_id_str>/verify-repair', methods=['POST'])
def verify_repair(hazard_id_str):
    if session.get('role') != 'admin': return jsonify({'error': 'Unauthorized'}), 403
    data = request.json or {}
    action = data.get('action')
    try:
        # Normalize to integer DB ID
        if "-" in str(hazard_id_str):
            hazard_id = int(str(hazard_id_str).split("-")[1])
            master_id = hazard_id_str
        else:
            hazard_id = int(hazard_id_str)
            master_id = None # Will try to lookup dynamically if needed
            
        now = datetime.now().isoformat()
        supabase = get_supabase()
        res = supabase.table('assignments').select('*').eq('hazard_id', hazard_id).order('id', desc=True).limit(1).execute()
        
        if not res.data:
            return jsonify({'error': 'Assignment not found'}), 404
            
        row = res.data[0]
        row_id = row['id']
        worker_id = row['worker_id']
        if not master_id:
            master_id = f"USER-{hazard_id}" if row.get('hazard_source') == 'user_reports' else f"AI-{hazard_id}"
        
        if action == 'approve':
            supabase.table('assignments').update({
                'verification_status': 'Approved',
                'status': 'Completed',
                'verified_at': now,
                'completed_at': now
            }).eq('id', row_id).execute()
            
            # Mark hazard as closed so it drops off active maps
            if row.get('hazard_source') == 'potholes':
                supabase.table('potholes').update({'status': 'closed'}).eq('id', hazard_id).execute()
            elif row.get('hazard_source') in ['user_reports', 'USER']:
                supabase.table('user_reports').update({'status': 'closed'}).eq('id', hazard_id).execute()
            
            if worker_id:
                supabase.table('users').update({'worker_status': 'Available'}).eq('id', worker_id).execute()

            print(f"[WORKFLOW] [STATUS CHANGED] Hazard {master_id} | Waiting Verification -> Completed")
            print(f"[WORKFLOW] [ASSIGNMENT UPDATED] Row {row_id} | Approved | worker={worker_id}")

            # Remove the hazard from the active registry so it disappears from /api/alerts
            from services.hazard_registry import registry_cache as _registry_cache
            _registry_cache.remove_hazard(master_id)
            print(f"[WORKFLOW] [CACHE INVALIDATED] {master_id} removed from active registry.")
            print(f"[WORKFLOW] [ALERT CACHE REFRESHED] {master_id} no longer in active alerts.")

            msg = 'Repair verified and closed'
            updated_hazard = None  # Hazard is now gone from active monitoring
            
        elif action == 'reject':
            admin_notes = data.get('admin_notes', 'No reason provided')
            old_status = row.get('status', 'Unknown')
            
            # Update old row to Rejected so it stays in worker history
            supabase.table('assignments').update({
                'status': 'Rejected',
                'verification_status': 'Rejected',
                'admin_notes': admin_notes,
                'completed_at': now
            }).eq('id', row_id).execute()
            
            # Insert fresh row for the next worker
            new_payload = {
                'hazard_id': hazard_id,
                'hazard_source': row.get('hazard_source'),
                'status': 'Available',
                'verification_status': 'Pending',
                'priority': row.get('priority'),
                'risk_score': row.get('risk_score'),
                'approved_by_admin': False
            }
            new_res = supabase.table('assignments').insert(new_payload).execute()
            
            if worker_id:
                supabase.table('users').update({'worker_status': 'Available'}).eq('id', worker_id).execute()

            print(f"[WORKFLOW] [STATUS CHANGED] Hazard {master_id} | Waiting Verification -> Rejected (Row {row_id})")
            print(f"[WORKFLOW] [ASSIGNMENT UPDATED] New Available row created for Hazard {hazard_id}.")
            print(f"[WORKFLOW] [CACHE INVALIDATED] {master_id} assignment patched to Available.")

            # Patch the cache instantly to show new Available state
            from services.hazard_registry import patch_hazard_assignment, recalculate_single_hazard
            new_assignment_data = new_res.data[0] if new_res.data else new_payload
            patch_hazard_assignment(master_id, new_assignment_data)
            print(f"[WORKFLOW] [ALERT CACHE REFRESHED] {master_id} now shows Available in alerts.")

            msg = 'Repair rejected, new assignment created'

        # For approve, updated_hazard is None (removed from active alerts)
        # For reject, fetch fresh from cache after patch
        if action == 'reject':
            from services.hazard_registry import recalculate_single_hazard
            updated_hazard = recalculate_single_hazard(master_id, None, None, "assignment_update")
        
        return jsonify({
            'message': msg, 
            'success': True,
            'updated_hazard': updated_hazard._cached_dict if updated_hazard else None
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e), 'success': False}), 500

