import math
from datetime import datetime, timedelta, timezone

def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * \
        math.sin(delta_lambda / 2.0) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def calculate_quality_score(yolo_conf, bbox_ratio, frame_quality, center_x_ratio):
    """
    Quality score formula:
    0.40 * (confidence * 100) + 0.30 * (bbox_ratio * 100) + 0.20 * frame_quality + 0.10 * (center_position * 100)
    """
    center_pos = 1.0 - abs(center_x_ratio - 0.5) * 2.0
    return (0.40 * yolo_conf * 100) + \
           (0.30 * bbox_ratio * 100) + \
           (0.20 * frame_quality) + \
           (0.10 * center_pos * 100)

def find_duplicate_pothole(supabase, lat1, lon1, pothole_type="pothole", search_radius_m=10.0, time_window_s=10):
    """
    Searches for duplicates of the same type within the given time window and distance.
    Returns the closest duplicate record, or None if no duplicates are found.
    """
    try:
        now = datetime.now(timezone.utc)
        time_ago = (now - timedelta(seconds=time_window_s)).isoformat()

        response = supabase.table("potholes") \
            .select("id, latitude, longitude, confidence, quality_score, severity, status, last_reported_at") \
            .eq("type", pothole_type) \
            .gte("last_reported_at", time_ago) \
            .execute()

        candidates = getattr(response, "data", [])
        if not candidates:
            return None

        best_candidate = None
        min_dist = float('inf')

        for record in candidates:
            lat2 = record.get("latitude")
            lon2 = record.get("longitude")
            if lat2 is None or lon2 is None:
                continue
                
            dist = haversine_distance(lat1, lon1, lat2, lon2)
            if dist <= search_radius_m and dist < min_dist:
                min_dist = dist
                best_candidate = record

        return best_candidate
    except Exception as e:
        print(f"[FIND DUPLICATE ERROR] {e}")
        return None

def compare_quality(new_score, old_score):
    """
    Returns True if the new score is strictly better than the old score.
    If the old score is None (e.g. legacy data), it assumes the new score is better.
    """
    if old_score is None:
        return True
    return float(new_score) > float(old_score)

def insert_new_pothole(supabase, payload):
    """
    Inserts a new pothole and returns the inserted ID.
    """
    try:
        new_p = supabase.table("potholes").insert(payload).execute()
        inserted_id = new_p.data[0].get("id") if getattr(new_p, "data", []) else None
        return inserted_id
    except Exception as e:
        print(f"[INSERT POTHOLE ERROR] {e}")
        raise e

def update_existing_pothole(supabase, record_id, old_record, new_payload):
    """
    Updates the existing pothole with new metrics, ensuring severity never downgrades,
    and updates status, review_required, and location.
    """
    try:
        # Avoid circular import by importing max_severity locally
        from routes.ai import max_severity
        
        final_severity = max_severity(old_record.get("severity", "low"), new_payload.get("severity", "low"))
        
        update_payload = {
            "confidence": new_payload["confidence"],
            "quality_score": new_payload["quality_score"],
            "severity": final_severity,
            "latitude": new_payload["latitude"],
            "longitude": new_payload["longitude"],
            "last_reported_at": new_payload["last_reported_at"],
            "status": new_payload["status"],
            "review_required": new_payload["review_required"]
        }
        supabase.table("potholes").update(update_payload).eq("id", record_id).execute()
        return record_id
    except Exception as e:
        print(f"[UPDATE POTHOLE ERROR] {e}")
        raise e

def refresh_duplicate_timestamp(supabase, record_id, new_timestamp):
    """
    Increments the report count and refreshes the last reported timestamp.
    """
    try:
        # Increment count using RPC
        supabase.rpc("increment_report_count", {"row_id": record_id}).execute()
        # Update last_reported_at
        supabase.table("potholes").update({"last_reported_at": new_timestamp}).eq("id", record_id).execute()
    except Exception as e:
        print(f"[REFRESH TIMESTAMP ERROR] {e}")
