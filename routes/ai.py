# ================= IMPORTS =================
import os
import re
import uuid
import time
import hashlib
import cv2
import numpy as np
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify

# Production-safe YOLO import
from ultralytics import YOLO
import torch
from concurrent.futures import ThreadPoolExecutor

# Global thread pool for background tasks (e.g., image upload)
executor = ThreadPoolExecutor(max_workers=4)

from config import Config
import logging
logger = logging.getLogger(__name__)

IS_RAILWAY = os.environ.get("RAILWAY_ENVIRONMENT", "").strip().lower() in ("true", "1", "yes")

from utils.detection_logger import DetectionLogger
from utils.helpers import (
    is_duplicate,
    upload_with_retry,
    db_insert_with_retry,
)

try:
    from PIL import Image
except Exception:
    Image = None

# ================= INIT =================
ai_bp = Blueprint("ai", __name__)

# ================= MODEL (LAZY LOADING) =================
model = None

def load_model(dlog: "DetectionLogger | None" = None):
    global model
    
    if model is None:
        if dlog:
            dlog.model_loading()
        print("Loading YOLO model...")
        print("📂 Current directory:", os.getcwd())
        print("📂 Files:", os.listdir())
        model_path = os.path.join("models", "best.pt")
        
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"❌ MODEL NOT FOUND at {model_path}. Please ensure it exists.")
            
        try:
            print("Loading model from:", os.path.abspath(model_path))
            model = YOLO(model_path)
            
            # PyTorch Optimizations for Live Detection FPS
            if torch.cuda.is_available():
                torch.backends.cudnn.benchmark = True
                
            if dlog:
                dlog.model_loaded()
            print("YOLO model loaded successfully.")
            print("MODEL CLASSES:", model.names)
        except Exception as e:
            print(f"❌ Error loading YOLO: {e}")
            raise e
    return model


# ================= TRIGGER STATE =================
trigger_flag      = False
last_trigger_time = 0
last_sensor       = {"diff": 0.0, "vib": 0.0, "spike_ms": 0}
processing        = False   # Global request lock — prevents duplicate inserts


@ai_bp.route("/trigger", methods=["POST"])
def trigger():
    """ESP32 hardware trigger. Stores sensor payload and signals Android to capture."""
    global trigger_flag, last_trigger_time, last_sensor
    now = time.time()
    if now - last_trigger_time < 3:
        return jsonify({"status": "ignored", "reason": "cooldown"})

    try:
        diff     = float(request.form.get("diff",     0) or 0)
        vib      = float(request.form.get("vib",      0) or 0)
        spike_ms = float(request.form.get("spike_ms", 0) or 0)
    except (ValueError, TypeError):
        diff, vib, spike_ms = 0.0, 0.0, 0.0

    last_sensor = {"diff": diff, "vib": vib, "spike_ms": spike_ms}
    trigger_flag      = True
    last_trigger_time = now
    print(f"[SENSOR] ESP32 TRIGGER | diff={diff} vib={vib} spike_ms={spike_ms}")
    return jsonify({"status": "ok", "diff": diff, "vib": vib, "spike_ms": spike_ms})


@ai_bp.route("/check", methods=["GET"])
def check():
    """Android polling endpoint. Returns capture=True once per trigger."""
    global trigger_flag
    if trigger_flag:
        trigger_flag = False
        print("📸 Capture signal sent to Android")
        return jsonify({"capture": True})
    return jsonify({"capture": False})





# ================= SEVERITY ORDERING =================
SEVERITY_RANK = {"low": 1, "medium": 2, "high": 3, "critical": 4}

def max_severity(a: str, b: str) -> str:
    """Return the higher of two severity strings. Never downgrade existing records."""
    return a if SEVERITY_RANK.get(a, 0) >= SEVERITY_RANK.get(b, 0) else b


SEVERITY_ORDER = ["low", "medium", "high", "critical"]

def bump_severity(level: str, step: int = 1) -> str:
    if level not in SEVERITY_ORDER:
        return level
    idx = min(len(SEVERITY_ORDER) - 1, SEVERITY_ORDER.index(level) + step)
    return SEVERITY_ORDER[idx]

def reduce_severity(level: str, step: int = 1) -> str:
    if level not in SEVERITY_ORDER:
        return level
    idx = max(0, SEVERITY_ORDER.index(level) - step)
    return SEVERITY_ORDER[idx]


def score_user_report_severity(img: np.ndarray, detections: list) -> dict:
    """
    Severity for user reports based on weighted factors:
    - Pothole size (bbox area)      40%
    - Number of potholes            30%
    - Average AI confidence          20%
    Returns severity tier (low, medium, high, critical) and weighted score.
    """
    h, w = img.shape[:2]
    img_area = float(max(1, h * w))

    valid = []
    for d in detections:
        conf = float(d.get("confidence", 0.0) or 0.0)
        # Filter detections below user report confidence threshold (0.5)
        if conf < 0.5:
            continue
        box = d.get("box") or [0, 0, 0, 0]
        x1, y1, x2, y2 = [int(max(0, v)) for v in box]
        x2 = min(x2, w - 1)
        y2 = min(y2, h - 1)
        bw = max(0, x2 - x1)
        bh = max(0, y2 - y1)
        ratio = (bw * bh) / img_area
        if ratio <= 0:
            continue
        valid.append({
            **d,
            "bbox_ratio": round(ratio, 6),
            "confidence": conf
        })

    # No detections -> N/A severity
    if not valid:
        return {
            "severity": None,
            "score": 0,
            "valid_detections": [],
            "primary": None
        }

    pothole_count = len(valid)
    avg_confidence = sum(d["confidence"] for d in valid) / pothole_count
    max_bbox_ratio = max(d["bbox_ratio"] for d in valid)

    # Weighted score (0-100) using specified percentages
    weighted_score = (
        40 * max_bbox_ratio +
        30 * (pothole_count / (pothole_count + 4)) +
        20 * avg_confidence
    ) * 100
    weighted_score = int(round(min(100, weighted_score)))

    # Determine severity tier
    if pothole_count >= 4 and avg_confidence >= 0.70:
        sev = "critical"
    elif pothole_count >= 2 or max_bbox_ratio > 0.15:
        sev = "high"
    elif pothole_count == 1:
        if max_bbox_ratio < 0.02:
            sev = "low"
        elif max_bbox_ratio < 0.08:
            sev = "medium"
        else:
            sev = "high"
    else:
        sev = "low"

    primary = max(valid, key=lambda d: d.get("bbox_ratio", 0.0))
    return {
        "severity": sev,
        "score": weighted_score,
        "valid_detections": valid,
        "primary": primary
    }



def road_scene_check(img: np.ndarray) -> bool:
    """
    Lightweight road/outdoor heuristic:
    - prefer texture in lower half
    - avoid very flat indoor-like regions
    """
    h, w = img.shape[:2]
    lower = img[h // 2:, :]
    gray = cv2.cvtColor(lower, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 60, 160)
    edge_density = float(np.mean(edges > 0))
    brightness = float(np.mean(gray))
    return edge_density > 0.02 and brightness > 30


def dominant_face_present(img: np.ndarray) -> bool:
    """
    Reject selfie-like captures where a face occupies major frame area.
    """
    try:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(60, 60))
        if len(faces) == 0:
            return False
        h, w = gray.shape[:2]
        img_area = float(max(1, h * w))
        max_face_area = max((fw * fh for (_, _, fw, fh) in faces), default=0.0)
        return (max_face_area / img_area) > 0.18
    except Exception:
        return False


def exif_metadata_valid(file_bytes: bytes) -> bool:
    if Image is None:
        return False
    try:
        from io import BytesIO
        pil_img = Image.open(BytesIO(file_bytes))
        exif = pil_img.getexif()
        if not exif:
            return False
        has_time = bool(exif.get(306) or exif.get(36867))  # DateTime / DateTimeOriginal
        has_device = bool(exif.get(271) or exif.get(272))  # Make / Model
        return has_time and has_device
    except Exception:
        return False


# ================= UPDATE EXISTING POTHOLE =================
def update_existing_pothole(supabase, pothole_id: int, new_severity: str):
    """
    Update an existing pothole record:
    - Severity is only raised, never lowered.
    - last_reported_at is always refreshed.
    - report_count is incremented via RPC.
    """
    try:
        # Fetch existing severity
        existing = supabase.table("potholes").select("severity").eq("id", pothole_id).execute()
        if existing.data:
            old_severity = existing.data[0].get("severity", "low")
            final_severity = max_severity(old_severity, new_severity)
        else:
            final_severity = new_severity

        supabase.table("potholes") \
            .update({
                "severity": final_severity,
                "last_reported_at": datetime.now(timezone.utc).isoformat()
            }) \
            .eq("id", pothole_id) \
            .execute()

        # Increment report count via RPC
        try:
            supabase.rpc("increment_report_count", {"row_id": pothole_id}).execute()
        except Exception as rpc_err:
            print(f"[DB] RPC increment failed (non-critical): {rpc_err}")

        print(f"[DB] Pothole {pothole_id} updated → severity={final_severity}, count++")
    except Exception as e:
        print(f"[DB] ❌ Update failed: {e}")


# ================= SPIKE VALIDATION =================
def classify_spike(spike_ms: float) -> str:
    """
    Categorize spike by duration:
      < 200ms  → noise
      200–600ms → pothole
      > 600ms  → speed_breaker
    """
    if spike_ms <= 0:
        return "unknown"  # Not yet reported by ESP32, don't block
    elif spike_ms < 200:
        return "noise"
    elif spike_ms <= 600:
        return "pothole"
    else:
        return "speed_breaker"


# ================= YOLO INFERENCE ON SINGLE FRAME =================
def run_inference(m, img: np.ndarray) -> tuple:
    """Run YOLO on a single image. Returns (results, detections_list)."""
    detections = []
    results = None
    
    if m is None:
        return None, []

    try:
        start = time.time()
        
        # 1. IMPROVED BLUR HANDLING
        # Fast moving vehicles cause motion blur. 
        # Extremely low Laplacian variance means the image is a complete smear.
        # Reduced from 5 to 3 to allow more realistically blurred road captures.
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
        if blur_score < 5:
            return None, []
        
        # 2. OPTIMIZED CONFIDENCE THRESHOLD
        # A 0.15 threshold ensures we don't miss slightly deformed potholes
        # captured at an angle, while the backend 'strong_detections' logic
        # still filters out pure noise later.
        with torch.no_grad():
            device = "cuda:0" if torch.cuda.is_available() else "cpu"
            results = m.predict(
                source=img,
                conf=0.08,
                iou=0.30,
                imgsz=640,
                device=device,
                half=torch.cuda.is_available(),
                verbose=False
            )
        elapsed = (time.time() - start) * 1000
        print(f"[AI] Inference: {elapsed:.0f}ms")
        
        h, w = img.shape[:2]
        img_area = float(max(1, h * w))
        
        for r in results:
            if r.boxes is None:
                continue
            for box in r.boxes:
                cls  = int(box.cls[0])
                conf = float(box.conf[0])
                x1, y1, x2, y2 = map(float, box.xyxy[0])
                w_px, h_px = x2 - x1, y2 - y1
                ratio = (max(0.0, w_px) * max(0.0, h_px)) / img_area

                if w_px <= 1 or h_px <= 1:
                    continue

                if ratio <= 0:
                    continue

                # Keep center position calculation for select_best_frame logic
                center_x = (x1 + x2) / 2.0
                center_y = (y1 + y2) / 2.0

                center_x_ratio = center_x / float(max(1.0, w))
                center_y_ratio = center_y / float(max(1.0, h))

                detections.append({
                    "type":       m.names[cls],
                    "confidence": round(conf, 2),
                    "box":        [round(x1, 1), round(y1, 1), round(x2, 1), round(y2, 1)],
                    "max_dim":    round(max(w_px, h_px), 1),
                    "bbox_ratio": round(ratio, 4),
                    "center_x_ratio": round(center_x_ratio, 4)
                })
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[AI] Inference error: {e}")
        raise e
    return results, detections


# ================= BEST FRAME SELECTION =================
def select_best_frame(frames: list) -> tuple:
    """
    Given a list of (results, detections, img, idx, quality) tuples,
    pick the Best 10 Live Frames with the highest weighted score.
    Returns (results, detections, img, idx, score) of the best frame.
    """
    best_score = -1
    best = frames[0]
    for frame in frames:
        results, detections, img, idx, quality = frame
        if detections:
            primary = max(detections, key=lambda d: d.get("bbox_ratio", 0.0))
            
            yolo_conf = primary.get("confidence", 0.0)
            bbox_ratio = primary.get("bbox_ratio", 0.0)
            center_x_ratio = primary.get("center_x_ratio", 0.5)
            
            center_pos = 1.0 - abs(center_x_ratio - 0.5) * 2.0
            
            score = (0.40 * yolo_conf * 100) + (0.30 * bbox_ratio * 100) + (0.20 * quality) + (0.10 * center_pos * 100)
            
            if score > best_score:
                best_score = score
                best = frame
    return (best[0], best[1], best[2], best[3], best_score)


# ================= AI SEVERITY CALCULATION =================
def decide_ai_severity(detections: list) -> str:
    """
    Severity is derived ONLY from:
      1. Number of potholes detected
      2. Average confidence of all detections
      3. Largest bounding-box ratio (max_bbox)

    Severity is completely independent of approval status.
    Evaluated top-down: the first matching tier wins.

    CRITICAL (highest)
        4+ potholes
        OR 2+ large potholes (max_bbox >= 0.30)
        OR largest pothole > 30% of image AND avg_conf > 70%

    HIGH
        3+ potholes
        OR largest pothole > 15% of image
        OR avg_conf > 70%

    MEDIUM
        2 potholes
        OR 1 medium-sized pothole (max_bbox >= 0.05)
        OR avg_conf 40–70%

    LOW (default)
        1 pothole, small size, avg_conf < 40%
    """
    if not detections:
        return "low"

    pothole_count = len(detections)
    avg_conf      = sum(d.get("confidence", 0.0) for d in detections) / pothole_count
    max_bbox      = max(d.get("bbox_ratio",  0.0) for d in detections)
    large_potholes = sum(1 for d in detections if d.get("bbox_ratio", 0.0) >= 0.15)

    print(
        f"[SEVERITY] count={pothole_count} "
        f"avg_conf={avg_conf:.4f} "
        f"max_bbox={max_bbox:.4f} "
        f"large={large_potholes}"
    )

    # ── CRITICAL ─────────────────────────────────────────────────────────────
    if (
        (pothole_count >= 4 and avg_conf >= 0.80)
        or (large_potholes >= 2 and avg_conf >= 0.70)
        or (max_bbox > 0.30 and avg_conf >= 0.70)
    ):
        return "critical"

    # ── HIGH ─────────────────────────────────────────────────────────────────
    if (
        pothole_count >= 3
        or (max_bbox > 0.15 and avg_conf >= 0.60)
    ):
        return "high"

    # ── MEDIUM ───────────────────────────────────────────────────────────────
    if (
        pothole_count >= 2
        or max_bbox >= 0.05
        or 0.40 <= avg_conf <= 0.70
    ):
        return "medium"

    # ── LOW (default) ────────────────────────────────────────────────────────
    return "low"



# ================= /analyze ENDPOINT =================
@ai_bp.route("/analyze", methods=["POST"])
def analyze():
    """
    Main fusion pipeline:
    1. Validate inputs
    2. Load sensor state
    3. Classify spike shape
    4. Run YOLO inference on all submitted frames
    5. Select best frame
    6. Decide severity (sensor authority)
    7. Upload annotated image
    8. Persist (insert or update duplicate)
    """
    global processing
    if processing:
        print("[FUSION] Already processing → skip")
        return jsonify({"status": "busy"})

    processing = True
    _t_total_start = time.time()
    dlog = DetectionLogger()

    try:
        from app import supabase

        # ----- Detect source (Android app vs generic API) -----
        ua = request.headers.get("User-Agent", "")
        source = "Android App" if ("okhttp" in ua.lower() or "dalvik" in ua.lower() or "android" in ua.lower()) else "API"
        first_file = request.files.getlist("image")
        first_fname = first_file[0].filename if first_file else "N/A"
        client_ip = request.headers.get("X-Forwarded-For", request.remote_addr)

        # Read lat/lon early for logging
        try:
            _lat_log = float(request.form.get("lat", "0"))
            _lon_log = float(request.form.get("lon", "0"))
        except Exception:
            _lat_log, _lon_log = 0.0, 0.0

        dlog.request_start(
            source=source,
            filename=first_fname,
            byte_size=None,
            latitude=_lat_log,
            longitude=_lon_log,
            user_id=None,
            client_ip=client_ip,
        )

        m = load_model(dlog)
        if m is None:
            print("[FUSION] Running sensor-only mode (YOLO unavailable)")
        
        # ----- 1. Selected Frames -----
        raw_files = request.files.getlist("image")
        qualities_str = request.form.getlist("frame_quality")

        if not raw_files:
            single = request.files.get("image")
            if single:
                raw_files = [single]
                single_q = request.form.get("frame_quality")
                qualities_str = [single_q] if single_q else []

        raw_files = [f for f in raw_files if f is not None]

        # SAFE GPS PARSING
        try:
            lat = float(request.form.get("lat", "0"))
            lon = float(request.form.get("lon", "0"))
        except Exception:
            lat = 0.0
            lon = 0.0

        phone_vibration = float(
            request.form.get("vibration", 0)
        )

        print(
            f"[PHONE VIBRATION] {phone_vibration}"
        )

        print("========== REQUEST DEBUG ==========")
        print("FILES COUNT:", len(raw_files))
        print("LAT:", lat)
        print("LON:", lon)

        # STRICT VALIDATION
        valid_files = []

        for i, f in enumerate(raw_files):
            try:
                data = f.read()

                if len(data) > 1000:
                    q_val = 100.0
                    try:
                        if i < len(qualities_str) and qualities_str[i]:
                            q_val = float(qualities_str[i])
                    except (ValueError, TypeError):
                        pass
                    valid_files.append((f, data, q_val))

            except Exception as e:
                print("[LIVE BUFFER ERROR]", e)

        files = valid_files
        request_filename = files[0][0].filename if files else "unknown"

        if len(files) == 0:
            return jsonify({
                "error": "No valid images"
            }), 400


        # ----- 2. Sensor State -----
        diff     = last_sensor.get("diff",     0.0)
        vib      = last_sensor.get("vib",      0.0)
        spike_ms = last_sensor.get("spike_ms", 0)
        sensor   = {"diff": diff, "vib": vib, "spike_ms": spike_ms}

        periodic_mode = diff <= 0.5

        # ----- 3. Spike Classification -----
        spike_class = classify_spike(spike_ms)
        if spike_class == "noise":
            return jsonify({"status": "ignored", "reason": "noise_spike"})
        if spike_class == "speed_breaker":
            return jsonify({"status": "ignored", "reason": "speed_breaker"})

        # ----- 4. Decode & Infer Best 10 Live Frames -----
        dlog.inference_start()
        _t_yolo_start = time.time()
        frames = []
        valid_frames = []

        for idx, item in enumerate(files):
            f, file_bytes, q_val = item
            np_arr = np.frombuffer(file_bytes, np.uint8)
            img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

            if img is None:
                continue

            # ===== DEBUG =====
            if not IS_RAILWAY:
                cv2.imwrite(f"received_{idx}.jpg", img)

            if m:
                results, detections = run_inference(m, img)
                frames.append((results, detections, img, idx, q_val))

                strong_detections = [
                    d for d in detections
                    if d["confidence"] >= 0.20
                ]

                if len(strong_detections) > 0:
                    valid_frames.append((results, strong_detections, img, idx, q_val))
            else:
                frames.append((None, [], img, idx, q_val))

        _yolo_ms = (time.time() - _t_yolo_start) * 1000

        if not frames:
            return jsonify({"error": "All frames invalid"}), 400

        # ----- 5. Best Frame Selection -----
        if len(valid_frames) == 0:
            dlog.no_detection()
            return jsonify({
                "success": False,
                "message": "No pothole detected"
            })

        best_results, best_detections, best_img, best_idx, best_score = select_best_frame(valid_frames)

        if len(best_detections) == 0:
            dlog.no_detection()
            return jsonify({
                "status": "ignored",
                "reason": "no_ai_detection"
            })

        # ----- Log each detection -----
        for i, det in enumerate(best_detections, start=1):
            dlog.detection(
                index=i,
                cls=det.get("type", "pothole"),
                conf=det.get("confidence", 0.0),
                box=det.get("box", [0, 0, 0, 0]),
            )
        dlog.summary(best_detections)

        # ----- 6. Decision Logic -----
        # ================= AI APPROVAL LOGIC =================
        if periodic_mode:
            best_conf = max(d["confidence"] for d in best_detections)
            print("[PERIODIC AI] CONF =", best_conf)
            print("[PERIODIC AI] DETECTIONS =", best_detections)

            # Confidence-based approval workflow
            # < 30%  → reject immediately (no upload, no DB)
            # 30-69% → pending in potholes (admin must approve)
            # >= 70% → auto-approved into potholes
            if best_conf < 0.30:
                dlog.log_rejected(request_filename, best_conf)
                dlog.request_end()
                return jsonify({"status": "rejected", "reason": "Detection confidence too low."})
            elif best_conf < 0.70:
                # Pending — goes into potholes with status='pending'
                approval_status = "pending"
                dlog.log_accepted(request_filename, best_conf)
            else:
                # Auto-approved — goes into potholes with status='approved'
                approval_status = "approved"
                dlog.log_accepted(request_filename, best_conf)

            # Severity is independent of approval status
            decision = decide_ai_severity(best_detections)
        else:
            # Sensor-triggered path: same confidence gates as periodic mode.
            # < 30%  → reject immediately (no upload, no DB)
            # 30-69% → pending in potholes
            # >= 70% → auto-approved
            _sensor_conf = max((d["confidence"] for d in best_detections), default=0.0)
            if _sensor_conf < 0.30:
                dlog.log_rejected(request_filename, _sensor_conf)
                dlog.request_end()
                return jsonify({"status": "rejected", "reason": "Detection confidence too low."})
            elif _sensor_conf < 0.70:
                approval_status = "pending"
            else:
                approval_status = "approved"

            # Severity is independent of approval status
            decision = decide_ai_severity(best_detections)

        if decision == "ignored":
            reason = "diff too low" if diff <= 10 else ("no AI detection" if not best_detections else "low confidence")
            return jsonify({
                "status":     "ignored",
                "decision":   decision,
                "diff":       diff,
                "spike_ms":   spike_ms,
                "detections": best_detections
            })

        # ----- 7. Select Primary Detection -----
        primary = max(best_detections, key=lambda d: d.get("bbox_ratio", 0.0))

        # ----- 8. Immediate Database Insert -----
        now_iso = datetime.now(timezone.utc).isoformat()
        inserted_id = None
        
        _t_db_start = time.time()
        dlog.db_saving()
        
        try:
            pothole_payload = {
                "latitude":         float(lat),
                "longitude":        float(lon),
                "severity":         str(decision),
                "confidence":       float(primary["confidence"]),
                "image_url":        None,   # To be updated by background upload
                "type":             "pothole",
                "pothole":          True,
                "status":           approval_status,
                "review_required":  approval_status == "pending",
                "report_count":     1,
                "created_at":       now_iso,
                "last_reported_at": now_iso,
            }
            # Use insert returning data
            new_p = supabase.table("potholes").insert(pothole_payload).execute()
            inserted_id = new_p.data[0].get("id") if getattr(new_p, "data", []) else None

                
        except Exception as e:
            import traceback
            traceback.print_exc()
            print("========== DB INSERT FAILED ==========")
            return jsonify({"status": "db_insert_failed", "error": str(e)}), 200

        _db_ms = (time.time() - _t_db_start) * 1000
        dlog.db_done(report_id=inserted_id)

        # ----- 9. Background Image Upload -----
        base_name = f"fusion_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        if best_results is not None:
            annotated = best_results[0].plot()
        else:
            annotated = best_img
            
        def background_upload(supabase_client, pid, b_name, img_array):
            _t_bg_start = time.time()
            try:
                # Encode to JPEG with default high quality. Do NOT resize.
                _, ann_buffer = cv2.imencode('.jpg', img_array)
                
                # Upload
                ann_filename = upload_with_retry(supabase_client, ann_buffer.tobytes(), f"{b_name}_annotated")
                
                if ann_filename:
                    final_url = f"{Config.SUPABASE_URL}/storage/v1/object/public/pothole-images/{ann_filename}"
                    supabase_client.table("potholes").update({"image_url": final_url}).eq("id", pid).execute()
            except Exception as e:
                pass
            _t_bg_ms = (time.time() - _t_bg_start) * 1000
            print(f"[PERFORMANCE] Background Upload Time: {_t_bg_ms:.2f}ms")

        if inserted_id:
            executor.submit(background_upload, supabase, inserted_id, base_name, annotated)

        # ----- 10. Immediate API Response -----
        _total_s = time.time() - _t_total_start
        print("========== PERFORMANCE LOGGING ==========")
        print(f"Received Frames: {len(raw_files)}")
        print(f"Valid Frames: {len(files)}")
        print(f"Frames Sent To YOLO: {len(frames)}")
        print(f"Best Frame Index: {best_idx}")
        print(f"Best Frame Score: {best_score:.2f}")
        print(f"YOLO Inference Time: {_yolo_ms:.2f}ms")
        print(f"Database Insert Time: {_db_ms:.2f}ms")
        print(f"Background Upload Time: Delegated to async thread")
        print(f"Total Request Time: {_total_s * 1000:.2f}ms")
        print("=========================================")

        dlog.timings(yolo_ms=_yolo_ms, upload_ms=0.0, db_ms=_db_ms, total_s=_total_s)
        dlog.request_end()
        
        return jsonify({
            "status":     "success",
            "decision":   decision,
            "diff":       diff,
            "spike_ms":   spike_ms,
            "detections": best_detections,
            "depth":      diff,
            "vibration":  phone_vibration,
            "fusion_enabled": True
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        dlog.error(e)
        print(f"[FUSION] ❌ Unhandled error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        processing = False


# ================= USER REPORT ENDPOINT =================
@ai_bp.route("/user-report", methods=["POST"])
def user_report():
    """Analyze a user report with hybrid AI logic and return preview payload."""
    from app import supabase

    _t_total_start = time.time()
    dlog = DetectionLogger()

    file = request.files.get("image")
    lat = request.form.get("lat") or request.form.get("latitude")
    lon = request.form.get("lon") or request.form.get("longitude")

    if not file or not lat or not lon:
        return jsonify({"error": "Missing image or location"}), 400

    try:
        lat_f = float(lat)
        lon_f = float(lon)
    except ValueError:
        return jsonify({"error": "Invalid coordinates"}), 400

    # Decode image once. AI uses this frame; upload uses annotated or original.
    try:
        file_bytes = file.read()  # Preserve original bytes from upload
        byte_size = len(file_bytes or b"")
        _t_decode_start = time.time()
        np_arr = np.frombuffer(file_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Decode failed")
        _decode_ms = (time.time() - _t_decode_start) * 1000
        print(f"Decode: {_decode_ms/1000:.2f}s")
    except Exception:
        return jsonify({"error": "Invalid image data"}), 400

    # ----- Detect source (Website vs Android vs API) -----
    ua = request.headers.get("User-Agent", "")
    referer = request.headers.get("Referer", "")
    if "okhttp" in ua.lower() or "dalvik" in ua.lower() or "android" in ua.lower():
        source = "Android App"
    elif referer or "mozilla" in ua.lower():
        source = "Website"
    else:
        source = "API"
    client_ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    user_id = None
    try:
        from flask import session as flask_session
        user_id = flask_session.get("user_id")
    except Exception:
        pass

    dlog.request_start(
        source=source,
        filename=file.filename or "N/A",
        byte_size=byte_size,
        latitude=lat_f,
        longitude=lon_f,
        user_id=user_id,
        client_ip=client_ip,
    )

    # Basic quality gates to reduce false detections.
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    brightness = float(np.mean(gray))
    bytes_per_pixel = (byte_size / float(max(1, w * h)))

    if blur_score < 10.0:
        return jsonify({"error": "image_too_blurry", "blur_score": round(blur_score, 2)}), 400
    if brightness < 20.0:
        return jsonify({"error": "image_too_dark", "brightness": round(brightness, 2)}), 400
    if bytes_per_pixel < 0.03:
        return jsonify({"error": "image_over_compressed"}), 400

    diff = request.form.get("diff", type=float, default=0.0)
    capture_source = (request.form.get("capture_source") or "live").strip().lower()
    capture_type = "upload" if capture_source in ("upload", "gallery_upload") else "live"
    strict_live_only = bool(getattr(Config, "STRICT_LIVE_CAPTURE_ONLY", False))
    gps_accuracy = request.form.get("gps_accuracy", type=float)
    image_hash = hashlib.sha256(file_bytes).hexdigest()

    m = load_model(dlog)
    ai_available = m is not None
    results = None
    allowed_detections = []
    top_detection = None
    _yolo_ms = 0.0  # default, overridden if AI runs

    if ai_available:
        try:
            dlog.inference_start()
            _t_yolo_start = time.time()
            print("✅ Starting AI inference...")
            print("MODEL CLASSES:", m.names)
            # Lightweight inference configuration for Render deployment.
            device = "cuda:0" if torch.cuda.is_available() else "cpu"
            results = m.predict(
                source=img,
                conf=0.10,
                iou=0.20,
                imgsz=320,
                device=device,
                half=torch.cuda.is_available(),
                verbose=False
            )
            _yolo_ms = (time.time() - _t_yolo_start) * 1000
            print(f"YOLO: {_yolo_ms/1000:.2f}s")
            for r in (results or []):
                if r.boxes is None:
                    continue
                for box in r.boxes:
                    cls = int(box.cls[0])
                    conf = float(box.conf[0])
                    class_name = str(m.names[cls]).lower()
                    
                    x1, y1, x2, y2 = map(float, box.xyxy[0])
                    bw = max(0.0, x2 - x1)
                    bh = max(0.0, y2 - y1)
                    
                    print(f"[DEBUG] Found {class_name} with confidence {conf:.2f}")

                    # Keep all raw detections at this stage — status logic below handles the 0.50 threshold
                    if conf < 0.10:
                        continue
                    
                    # Lowered strictness: allow smaller boxes for testing sensitivity
                    if bw < 10 or bh < 10:
                        print(f"[DEBUG] Skipping {class_name} (too small: {bw}x{bh})")
                        continue
                    
                    det = {
                        "type": class_name,
                        "confidence": round(conf, 4),
                        "box": [round(v) for v in (x1, y1, x2, y2)],
                        "bbox_ratio": round((bw * bh) / (w * h), 4),
                        "center_x_ratio": round((x1 + bw/2.0) / w, 4)
                    }
                    allowed_detections.append(det)
                    if top_detection is None or conf > top_detection["confidence"]:
                        top_detection = det
            print("DETECTIONS:", allowed_detections)
        except Exception as e:
            import traceback
            traceback.print_exc()
            dlog.error(e)
            print(f"[USER REPORT] AI inference failed: {e}")
            return jsonify({"error": "AI inference failed", "details": str(e)}), 500
    else:
        _yolo_ms = 0.0

    # Log each raw detection
    for i, det in enumerate(allowed_detections, start=1):
        dlog.detection(
            index=i,
            cls=det.get("type", "pothole"),
            conf=det.get("confidence", 0.0),
            box=det.get("box", [0, 0, 0, 0]),
        )
    dlog.summary(allowed_detections)

    confidence = float(top_detection["confidence"]) if top_detection else 0.0
    pothole_detected = top_detection is not None
    bbox_ratio = float(top_detection.get("bbox_ratio", 0.0) or 0.0) if top_detection else 0.0

    # New strict verification workflow
    status = "pending"
    severity = None
    severity_score = 0
    valid_detections = []  # default — overridden below when pothole passes threshold
    review_required = True

    if not pothole_detected:
        confidence = 0.0
        status = "rejected"
        review_required = False
        severity = None
        severity_score = 0
        dlog.no_detection()
    elif confidence == 0.0:
        status = "rejected"
        review_required = False
        severity = None
        severity_score = 0
        dlog.log_rejected(file.filename or "N/A", confidence)
    elif confidence < 0.30:
        status = "rejected"
        review_required = False
        severity = "low"
        severity_score = 1
        dlog.log_rejected(file.filename or "N/A", confidence)
    elif confidence < 0.50:
        status = "pending"
        review_required = True
        severity = "low"
        severity_score = 1
        dlog.log_accepted(file.filename or "N/A", confidence)
    else:
        if confidence < 0.70:
            status = "pending"
            review_required = True
        else:
            status = "approved"
            review_required = False
            
        # Calculate severity dynamically for >= 50%
        severity_eval = score_user_report_severity(img, allowed_detections if ai_available else [])
        severity = severity_eval["severity"]
        severity_score = int(severity_eval["score"])
        valid_detections = severity_eval["valid_detections"]
        primary_valid = severity_eval["primary"]
        if primary_valid:
            bbox_ratio = float(primary_valid.get("bbox_ratio", bbox_ratio) or bbox_ratio)
        dlog.log_accepted(file.filename or "N/A", confidence)

    # Security and anti-fake validations
    live_capture_verified = capture_type == "live" or capture_source in ("live_camera", "live")
    gps_verified = (gps_accuracy is not None and gps_accuracy <= 120.0) or (lat_f is not None and lon_f is not None)
    road_scene_valid = road_scene_check(img)
    face_dominant = dominant_face_present(img)
    metadata_valid = exif_metadata_valid(file_bytes)
    suspicious_reasons = []

    duplicate_image = False
    try:
        dup = supabase.table("user_reports").select("id").eq("image_hash", image_hash).limit(1).execute()
        duplicate_image = bool(getattr(dup, "data", []) or [])
    except Exception:
        duplicate_image = False

    if not road_scene_valid:
        suspicious_reasons.append("non_road_scene")
    if face_dominant:
        suspicious_reasons.append("face_dominant")
    if duplicate_image:
        suspicious_reasons.append("duplicate_image")
    if not metadata_valid:
        suspicious_reasons.append("missing_exif")

    trust_score = 0
    trust_score += 30 if live_capture_verified else 0
    trust_score += 20 if gps_verified else 0
    trust_score += 20 if road_scene_valid else 0
    trust_score += 20 if (pothole_detected and confidence >= 0.50 and bbox_ratio >= 0.01) else 0
    trust_score += 10 if metadata_valid else 0
    if capture_type == "upload":
        trust_score -= 25
    if not gps_verified:
        trust_score -= 20
    if duplicate_image:
        trust_score -= 25
    trust_score = int(max(0, min(100, trust_score)))

    if trust_score > 80:
        trust_level = "trusted"
    elif trust_score >= 50:
        trust_level = "review"
    else:
        trust_level = "untrusted"

    print(f"[USER REPORT] status={status} conf={confidence:.4f}")

    # Upload resized annotated image only (raw image is NOT stored)
    dlog.upload_start()
    _t_upload_start = time.time()
    
    base_name = f"user_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    annotated_filename = f"{base_name}_ann.jpg"
    image_url = f"{Config.SUPABASE_URL}/storage/v1/object/public/pothole-images/{annotated_filename}"
    _upload_ms = 0.0

    def process_and_upload(app_supabase, img_to_process, ai_results, b_name, a_filename, dl):
        try:
            _orig_h, _orig_w = img_to_process.shape[:2]
            _, _orig_buf = cv2.imencode(".jpg", img_to_process)
            print(f"[PERF] Original Resolution : {_orig_w}x{_orig_h}")
            print(f"[PERF] Original File Size  : {_orig_buf.nbytes} bytes")

            _t_bbox_start = time.time()
            annotated_or_raw = ai_results[0].plot() if (ai_results and len(ai_results) > 0) else img_to_process
            _bbox_ms = (time.time() - _t_bbox_start) * 1000
            print(f"Draw: {_bbox_ms/1000:.2f}s")

            _t_resize_start = time.time()
            h, w = annotated_or_raw.shape[:2]
            MAX_WIDTH = 1280
            if w > MAX_WIDTH:
                scale = MAX_WIDTH / float(w)
                annotated_or_raw = cv2.resize(
                    annotated_or_raw,
                    (MAX_WIDTH, int(h * scale)),
                    interpolation=cv2.INTER_AREA
                )
            _resize_ms = (time.time() - _t_resize_start) * 1000
            print(f"Resize: {_resize_ms/1000:.2f}s")

            _t_jpeg_start = time.time()
            ok_annotated, annotated_buffer = cv2.imencode(
                ".jpg", annotated_or_raw,
                [int(cv2.IMWRITE_JPEG_QUALITY), 85]
            )
            if not ok_annotated:
                raise ValueError("cv2.imencode failed")
            _jpeg_ms = (time.time() - _t_jpeg_start) * 1000
            print(f"JPEG: {_jpeg_ms/1000:.2f}s")
            
            print(f"[PERF] Resized Resolution  : {annotated_or_raw.shape[1]}x{annotated_or_raw.shape[0]}")
            print(f"[PERF] Compressed Size     : {annotated_buffer.nbytes} bytes")

            dl.image_saved()
            
            _t_upload_req_start = time.time()
            uploaded = upload_with_retry(app_supabase, annotated_buffer.tobytes(), f"{b_name}_ann", exact_filename=a_filename)
            _upload_req_ms = (time.time() - _t_upload_req_start) * 1000
            print(f"Upload: {_upload_req_ms/1000:.2f}s")
            
            if uploaded:
                dl.upload_done(url=f"{Config.SUPABASE_URL}/storage/v1/object/public/pothole-images/{uploaded}")
            else:
                print("[BACKGROUND UPLOAD] Upload failed, returned None")
        except Exception as e:
            import traceback
            traceback.print_exc()
            dl.error(e)
            print(f"[BACKGROUND UPLOAD] image processing/upload prep failed: {e}")

    if IS_RAILWAY:
        print("[USER REPORT] Railway environment detected - offloading image processing and upload to background thread.")
        executor.submit(process_and_upload, supabase, img, results, base_name, annotated_filename, dlog)
    else:
        print("[USER REPORT] Local environment detected - processing synchronously.")
        process_and_upload(supabase, img, results, base_name, annotated_filename, dlog)
        _upload_ms = (time.time() - _t_upload_start) * 1000
        print(f"[PERF] Sync Upload Time         : {_upload_ms:.1f} ms")

    _total_s = time.time() - _t_total_start
    print(f"Total: {_total_s:.2f}s")
    dlog.timings(yolo_ms=_yolo_ms, upload_ms=_upload_ms, total_s=_total_s)
    dlog.request_end()

    # Determine response message based on status
    response_payload = {
        "upload_id": base_name,
        "status": status,
        "ai_status": status,
        "review_required": review_required,
        "confidence": round(confidence, 4),
        "severity": severity,
        "severity_score": severity_score,
        "bbox_ratio": round(bbox_ratio, 4),
        "diff": round(float(diff or 0), 2),
        "trust_score": trust_score,
        "trust_level": trust_level,
        "live_capture_verified": live_capture_verified,
        "gps_verified": gps_verified,
        "road_scene_valid": road_scene_valid,
        "metadata_valid": metadata_valid,
        "duplicate_image": duplicate_image,
        "suspicious_reasons": suspicious_reasons,
        "capture_source": capture_source,
        "capture_type": capture_type,
        "image_hash": image_hash,
        "detections": valid_detections if valid_detections else allowed_detections,
        "pothole_detected": pothole_detected,
        "image_url": image_url,
        "latitude": lat_f,
        "longitude": lon_f
    }
    if status == "rejected" and not pothole_detected:
        response_payload["message"] = "not detected anything"
    return jsonify(response_payload)



@ai_bp.route("/user-report/submit", methods=["POST"])
def submit_user_report():
    """Persist analyzed user report and route approved ones to potholes."""
    from app import supabase

    _t_total_start = time.time()
    dlog = DetectionLogger()

    data = request.get_json(silent=True) or {}
    required = [
        "latitude", "longitude", "image_url",
        "status", "confidence", "severity"
    ]
    if any(k not in data for k in required):
        return jsonify({"error": "Missing analyzed report fields"}), 400

    try:
        lat_f = float(data["latitude"])
        lon_f = float(data["longitude"])
        confidence = float(data["confidence"])
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid numeric fields"}), 400

    ai_status = str(data.get("status", "pending")).lower()
    
    if ai_status == "rejected" or confidence < 0.30 or confidence == 0.0:
        # Confidence too low — discard silently
        status = "rejected"
        severity = None
        review_required = False
    elif confidence < 0.70:
        # Confidence 0.30–0.69 → send to admin review queue
        status = "pending"
        raw_sev = data.get("severity")
        severity = str(raw_sev).lower() if raw_sev is not None and str(raw_sev).lower() not in ["none", "null", "n/a"] else None
        review_required = True
    else:
        # Confidence ≥ 0.70 → auto-approved
        status = "approved"
        raw_sev = data.get("severity")
        severity = str(raw_sev).lower() if raw_sev is not None and str(raw_sev).lower() not in ["none", "null", "n/a"] else None
        review_required = False
    detections = data.get("detections", [])
    detection_type = detections[0]["type"] if detections else "none"
    upload_id = data.get("upload_id")
    bbox_ratio = float(data.get("bbox_ratio", 0.0) or 0.0)
    diff_val = float(data.get("diff", 0.0) or 0.0)
    trust_score = int(float(data.get("trust_score", 0) or 0))
    trust_level = str(data.get("trust_level") or "review")
    capture_source = str(data.get("capture_source") or "live")
    capture_type = str(data.get("capture_type") or ("upload" if capture_source in ("upload", "gallery_upload") else "live"))
    image_hash = data.get("image_hash")
    now_iso = datetime.now(timezone.utc).isoformat()

    # Log submit request
    client_ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    ua = request.headers.get("User-Agent", "")
    if "okhttp" in ua.lower() or "dalvik" in ua.lower() or "android" in ua.lower():
        source = "Android App"
    elif "mozilla" in ua.lower():
        source = "Website"
    else:
        source = "API"
    dlog.request_start(
        source=f"{source} [submit]",
        filename=data.get("image_url", "N/A").split("/")[-1],
        byte_size=None,
        latitude=lat_f,
        longitude=lon_f,
        user_id=None,
        client_ip=client_ip,
    )

    def insert_with_missing_column_retry(table_name: str, payload: dict, max_retries: int = 10):
        current = dict(payload)
        for _ in range(max_retries):
            try:
                return supabase.table(table_name).insert(current).execute(), current
            except Exception as e:
                err = str(e)
                # Handle both single and double quotes in Supabase Postgres error messages
                m = re.search(r"Could not find the ['\"]([^'\"]+)['\"] column", err)
                if m and m.group(1) in current:
                    missing_col = m.group(1)
                    current.pop(missing_col, None)
                    print(f"[DB] {table_name} missing column '{missing_col}', retrying")
                    continue
                # Fallback: if we know common missing columns, just try stripping them
                if "column" in err.lower() and "upload_id" in current:
                    print(f"[DB] Attempting aggressive fallback: popping upload_id, report_id, etc.")
                    current.pop("upload_id", None)
                    current.pop("report_id", None)
                    current.pop("source_report_id", None)
                    current.pop("source_type", None)
                    continue
                raise
        raise RuntimeError(f"{table_name} insert retries exhausted")

    # Always insert into user_reports
    user_payload = {
        "latitude": lat_f,
        "longitude": lon_f,
        "media_url": data["image_url"],
        "image_url": data["image_url"],
        "upload_id": upload_id,
        "type": "image",
        "description": f"AI Decision: {ai_status}",
        "status": status,
        "ai_status": ai_status,
        "review_required": review_required,
        "confidence": round(confidence, 4),
        "severity": severity,
        "trust_score": trust_score,
        "trust_level": trust_level,
        "source_type": capture_type,
        "capture_type": capture_type,
        "image_hash": image_hash,
        "created_at": now_iso
    }

    dlog.db_saving()
    _t_db_start = time.time()
    user_report_id = None
    try:
        user_res, inserted_user_payload = insert_with_missing_column_retry("user_reports", user_payload)
        user_rows = getattr(user_res, "data", []) or []
        user_report_id = user_rows[0].get("id") if user_rows else None
        dlog.db_done(report_id=user_report_id)
    except Exception as e:
        print(f"[DB] user_reports rich insert failed, trying minimal fallback: {e}")
        try:
            minimal_payload = {
                "latitude": lat_f,
                "longitude": lon_f,
                "media_url": data["image_url"],
                "status": status,
                "type": "image",
                "description": f"AI Decision: {ai_status}"
            }
            user_res, _ = insert_with_missing_column_retry("user_reports", minimal_payload)
            user_rows = getattr(user_res, "data", []) or []
            user_report_id = user_rows[0].get("id") if user_rows else None
            dlog.db_done(report_id=user_report_id)
        except Exception as e2:
            dlog.error(e2)
            print(f"[DB] ❌ user_reports minimal insert failed: {e2}")
            return jsonify({"error": "user_report_insert_failed", "detail": str(e2)}), 500
    _db_ms = (time.time() - _t_db_start) * 1000
    print(f"Database: {_db_ms/1000:.2f}s")

    # Only approved go into potholes
    if status == "approved":
        try:
            # Prevent duplicate pothole insert for same analyzed upload.
            existing = supabase.table("potholes").select("id").eq("image_url", data["image_url"]).limit(1).execute()
            if getattr(existing, "data", []):
                print("[DB] Skipping pothole insert (already exists for this upload image)")
            else:
                pothole_payload = {
                    "upload_id": upload_id,
                    "report_id": user_report_id,
                    "source_report_id": user_report_id,
                    "latitude": lat_f,
                    "longitude": lon_f,
                    "severity": severity or "medium", # Fallback so frontend doesn't ignore it
                    "image_url": data["image_url"],
                    "confidence": round(confidence, 4),
                    "type": detection_type if detection_type in ["pothole", "crack"] else "pothole",
                    "pothole": True,
                    "status": "approved",
                    "report_count": 1,
                    "created_at": now_iso,
                    "last_reported_at": now_iso
                }
                insert_with_missing_column_retry("potholes", pothole_payload)
        except Exception as e:
            print(f"[DB] potholes insert failed: {e}")

    # Keep user report status synchronized for non-approved paths as source of truth.
    if status in ("pending", "rejected"):
        try:
            supabase.table("user_reports").update({
                "status": status
            }).eq("id", user_report_id).execute()
        except Exception:
            pass

    _total_s = time.time() - _t_total_start
    print(f"[PERF] Total Request Time: {_total_s * 1000:.2f} ms")
    dlog.timings(db_ms=_db_ms, total_s=_total_s)
    dlog.request_end()

    print(f"[USER REPORT] status={status} conf={confidence:.4f}")
    return jsonify({
        "message": "Report saved",
        "status": status,
        "confidence": round(confidence, 4),
        "severity": severity
    }), 201
