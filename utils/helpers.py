import math
import time
from datetime import datetime, timezone

def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return distance in metres between two GPS coordinates."""
    R = 6_371_000  # Earth radius in metres
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi  = math.radians(lat2 - lat1)
    dlam  = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def is_duplicate(supabase, lat: float, lon: float, threshold_m: float = 50.0):
    """
    Checks if a pothole exists within threshold_m using a bounding box filter (±0.0005 deg).
    Returns existing pothole record if found, else None.
    """
    try:
        # Bounding box filter for performance (approx 55m at 0.0005)
        res = supabase.table("potholes")\
            .select("*")\
            .eq("pothole", True)\
            .gte("latitude", lat - 0.0005)\
            .lte("latitude", lat + 0.0005)\
            .gte("longitude", lon - 0.0005)\
            .lte("longitude", lon + 0.0005)\
            .execute()
            
        for p in res.data:
            dist = haversine(lat, lon, float(p["latitude"]), float(p["longitude"]))
            if dist < threshold_m:
                return p
    except Exception as e:
        print(f"Duplicate check error: {e}")
        
    return None


def count_nearby_potholes(supabase, lat: float, lon: float, radius_m: float = 5.0):
    """
    Counts potholes within radius_m using a bounding box filter (±0.0001 deg ~ 11m).
    """
    try:
        # Bounding box for 5m (approx 0.00005)
        res = supabase.table("potholes")\
            .select("id, latitude, longitude")\
            .eq("pothole", True)\
            .gte("latitude", lat - 0.0001)\
            .lte("latitude", lat + 0.0001)\
            .gte("longitude", lon - 0.0001)\
            .lte("longitude", lon + 0.0001)\
            .execute()
        
        count = 0
        for p in res.data:
            if haversine(lat, lon, float(p["latitude"]), float(p["longitude"])) <= radius_m:
                count += 1
        return count
    except Exception as e:
        print(f"Count nearby error: {e}")
        return 0


def filter_by_confidence(records: list, threshold: float = 0.5) -> list:
    """
    Remove records whose confidence is below threshold.
    Manual reports (without confidence field) are always kept (treated as 1.0).
    """
    valid = []
    for r in records:
        conf = r.get("confidence")
        sev = r.get("severity")
        
        # 1. Reject invalid severity (even if admin approved)
        if sev is None or str(sev).lower() in ["none", "null", "n/a", ""]:
            continue
            
        # 2. Reject 0.0 confidence (even if admin approved)
        if conf is not None:
            c = float(conf)
            if c == 0.0:
                continue
        else:
            c = None
            
        status = str(r.get("status") or "").lower()
        ai_status = str(r.get("ai_status") or "").lower()
        source_report_id = r.get("source_report_id")

        # Bypass confidence filter if manually approved by admin (potholes table)
        # source_report_id is set to the real user_report id (positive int) when admin approves
        if source_report_id is not None:
            valid.append(r)
            continue

        # Bypass confidence filter if manually approved by admin (user_reports table)
        if status == "approved" and ai_status in ["pending", "rejected"]:
            valid.append(r)
            continue
            
        if c is not None:
            if c < threshold:
                continue
            
        valid.append(r)
    return valid


def majority_severity(severities: list) -> str:
    """
    Return the most-frequent (majority) severity from a list of severity strings.
    Only counts valid values: low, medium, high, critical.
    Falls back to 'medium' when the list is empty or all values are invalid.

    Example:
        majority_severity(["low","low","medium","high"]) → "low"
    """
    VALID = {"low", "medium", "high", "critical"}
    counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    for s in severities:
        key = str(s or "").lower().strip()
        if key in VALID:
            counts[key] += 1
    total = sum(counts.values())
    if total == 0:
        return "medium"
    # Return the severity with the highest vote count
    return max(counts, key=lambda k: counts[k])


def calculate_risk_score(severity, report_count):
    """
    Calculates a risk score based on severity and report count.
    Distinct values to allow cumulative calculation.
    """
    severity_map = {"low": 10, "medium": 25, "high": 45}
    sev_val = severity_map.get(str(severity).lower(), 25)
    
    # Reports add extra danger (capped)
    report_bonus = min(20, int(report_count or 0) * 3)
    
    return sev_val + report_bonus


def allowed_file(filename: str, allowed: set) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed


def human_time(dt_str: str) -> str:
    """Convert ISO timestamp to human readable relative time."""
    if not dt_str: return "unknown"
    try:
        from datetime import datetime, timezone
        import math
        
        # Parse timestamp (handle Z and offset formats)
        try:
            dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        except:
            dt = datetime.strptime(dt_str.split('.')[0], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
            
        now = datetime.now(timezone.utc)
        diff = (now - dt).total_seconds()
        
        if diff < 0: diff = 0 # Future safety
        if diff < 60: return "just now"
        if diff < 3600: return f"{math.floor(diff/60)} min ago"
        if diff < 86400: return f"{math.floor(diff/3600)} hours ago"
        if diff < 604800: return f"{math.floor(diff/86400)} days ago"
        return dt.strftime("%b %d, %Y")
    except Exception as e:
        print(f"Time parse error: {e}")
        return dt_str

def upload_with_retry(supabase, img_bytes: bytes, base_name: str, bucket_name: str = "pothole-images") -> str | None:
    """Upload image bytes to Supabase storage with exponential backoff.

    Args:
        supabase: Supabase client instance.
        img_bytes: Raw image bytes.
        base_name: Base name for the file (without extension or retry suffix).
        bucket_name: Supabase storage bucket.

    Returns:
        The filename on success, or ``None`` on failure.
    """
    import logging
    import traceback
    import time
    import httpx

    logger = logging.getLogger(__name__)
    backoff_times = [1, 2, 4]
    for attempt, wait in enumerate(backoff_times, start=1):
        try:
            filename = f"{base_name}_{attempt}.jpg"
            logger.info(f"[UPLOAD] Attempt {attempt}: uploading {filename} to bucket '{bucket_name}'")
            response = supabase.storage.from_(bucket_name).upload(
                path=filename,
                file=img_bytes,
                file_options={"content-type": "image/jpeg"},
            )
            # If the SDK returns a dict-like object with a 'Key' or similar, treat as success.
            logger.info(f"[UPLOAD] Successfully uploaded {filename}")
            return filename
        except httpx.ReadError as e:
            logger.warning(f"[UPLOAD] ReadError on attempt {attempt}: {e}")
        except httpx.ConnectError as e:
            logger.warning(f"[UPLOAD] ConnectError on attempt {attempt}: {e}")
        except httpx.RemoteProtocolError as e:
            logger.warning(f"[UPLOAD] RemoteProtocolError on attempt {attempt}: {e}")
        except httpx.TransportError as e:
            logger.warning(f"[UPLOAD] TransportError on attempt {attempt}: {e}")
        except Exception as e:
            logger.error(f"[UPLOAD] Unexpected error on attempt {attempt}: {e}", exc_info=True)
        logger.debug("[UPLOAD] Backing off for %s seconds before retry", wait)
        time.sleep(wait)
    logger.error("[UPLOAD] All retry attempts failed for %s", base_name)
    return None

def db_insert_with_retry(supabase, record: dict, retries: int = 3) -> bool:
    """
    Insert a pothole record into Supabase, retrying up to `retries` times.
    On 'Could not find column' errors (PGRST204 schema cache miss) the
    offending column is stripped from the payload and the insert is retried
    automatically — this prevents a single missing/extra column from blocking
    the entire detection pipeline.
    """
    import re as _re
    import traceback
    current = dict(record)  # Work on a copy so we don't mutate the caller's dict
    attempt = 0
    while attempt < retries:
        attempt += 1
        try:
            supabase.table("potholes").insert(current).execute()
            print(f"[DB] ✅ Saved to potholes on attempt {attempt}")
            return True
        except Exception as e:
            err = str(e)
            # Auto-strip columns that are not in the schema cache (PGRST204)
            m = _re.search(r"Could not find the ['\"]([^'\"]+)['\"] column", err)
            if m:
                col = m.group(1)
                if col in current:
                    current.pop(col)
                    print(f"[DB] Column '{col}' not in schema cache — stripped, retrying")
                    continue   # retry immediately (don't count against attempts)
            print(f"[DB] Insert attempt {attempt}/{retries} failed: {err}")
            traceback.print_exc()
            if attempt < retries:
                time.sleep(1)
    print("[DB] ❌ All insert attempts exhausted.")
    return False
