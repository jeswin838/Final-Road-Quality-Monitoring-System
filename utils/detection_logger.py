"""
utils/detection_logger.py
=========================
Centralised, structured terminal logging for pothole-detection requests.

Usage:
    from utils.detection_logger import DetectionLogger
    log = DetectionLogger()
    log.request_start(source="Website", filename="road.jpg", ...)
    log.model_loading()
    log.model_loaded()
    log.inference_start()
    log.detection(index=1, cls="pothole", conf=0.92, box=[120,85,340,250])
    log.no_detection()
    log.summary(detections=[...])
    log.image_saved()
    log.upload_start()
    log.upload_done(url="https://...")
    log.db_saving()
    log.db_done(report_id=42)
    log.timings(yolo_ms=234, upload_ms=120, db_ms=80, total_s=1.2)
    log.request_end()
    log.error(exc)
"""

import logging
import traceback
import os
from datetime import datetime

# ---------------------------------------------------------------------------
# Configure the root logger once
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("detection")

SEP  = "=" * 50
DASH = "-" * 50


def _fmt_size(byte_count: int) -> str:
    """Convert raw byte count to a human-readable KB / MB string."""
    if byte_count is None:
        return "N/A"
    if byte_count >= 1_048_576:
        return f"{byte_count / 1_048_576:.2f} MB"
    return f"{byte_count / 1024:.2f} KB"


class DetectionLogger:
    """All logging calls for one detection request."""

    # ------------------------------------------------------------------
    # Request boundary
    # ------------------------------------------------------------------
    def request_start(
        self,
        *,
        source: str = "Unknown",
        filename: str = "N/A",
        byte_size: int = None,
        latitude=None,
        longitude=None,
        user_id=None,
        client_ip: str = "N/A",
    ):
        logger.info(SEP)
        logger.info("🚀 New Detection Request")
        logger.info(f"🕒 Timestamp : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"🌐 Source    : {source}")
        logger.info(f"📷 Image Name: {filename}")
        logger.info(f"📁 Image Size: {_fmt_size(byte_size)}")
        logger.info(f"📍 Latitude  : {latitude if latitude is not None else 'N/A'}")
        logger.info(f"📍 Longitude : {longitude if longitude is not None else 'N/A'}")
        logger.info(f"👤 User ID   : {user_id if user_id is not None else 'N/A'}")
        logger.info(f"🌐 Client IP : {client_ip}")

    def request_end(self):
        logger.info("✅ Detection request completed successfully.")
        logger.info(SEP)

    # ------------------------------------------------------------------
    # New Workflow Specific Logging
    # ------------------------------------------------------------------
    def log_rejected(self, filename: str, confidence: float):
        logger.info(SEP)
        logger.info("🚀 New Detection Request")
        logger.info(f"📷 Image: {filename}")
        logger.info("🕳  Pothole Detected")
        logger.info(f"🎯 Confidence: {confidence * 100:.2f}%")
        logger.info("❌ Rejected (Below Threshold)")
        logger.info("💾 Database Save: NO")
        logger.info("☁  Storage Upload: NO")
        logger.info(SEP)

    def log_accepted(self, filename: str, confidence: float):
        logger.info(SEP)
        logger.info("🚀 New Detection Request")
        logger.info(f"📷 Image: {filename}")
        logger.info("🕳  Pothole Detected")
        logger.info(f"🎯 Confidence: {confidence * 100:.2f}%")
        logger.info("✅ Accepted")
        logger.info("☁  Uploading Images...")
        logger.info("💾 Saved to user_reports")
        logger.info("Status: Pending Admin Review")
        logger.info(SEP)

    def log_admin_approved(self, report_id):
        logger.info(SEP)
        logger.info("✅ Admin Approved Report")
        logger.info(f"📄 Report ID: {report_id}")
        logger.info("📤 Copied to potholes table")
        logger.info("📊 Dashboard Updated")
        logger.info("🗺  Map Updated")
        logger.info("📷 Image Logs Updated")
        logger.info(SEP)

    # ------------------------------------------------------------------
    # Model
    # ------------------------------------------------------------------
    def model_loading(self):
        logger.info("🤖 Loading YOLO model...")

    def model_loaded(self):
        logger.info("✅ Model loaded successfully.")

    def inference_start(self):
        logger.info("🤖 Running YOLO inference...")
        logger.info("⏳ Processing...")

    # ------------------------------------------------------------------
    # Per-detection
    # ------------------------------------------------------------------
    def detection(self, *, index: int, cls: str, conf: float, box: list):
        x1, y1, x2, y2 = (round(v) for v in box)
        logger.info(DASH)
        logger.info(f"🕳  Detection #{index}")
        logger.info(f"📌 Class      : {cls}")
        logger.info(f"🎯 Confidence : {conf * 100:.2f}%")
        logger.info("📍 Bounding Box:")
        logger.info(f"   x1={x1}")
        logger.info(f"   y1={y1}")
        logger.info(f"   x2={x2}")
        logger.info(f"   y2={y2}")
        logger.info(DASH)

    def no_detection(self):
        logger.info("❌ No potholes detected.")
        logger.info("📊 Total Objects Detected: 0")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    def summary(self, detections: list):
        """
        detections — list of dicts with at least a 'confidence' key.
        """
        count = len(detections)
        if count == 0:
            self.no_detection()
            return

        confs = [float(d.get("confidence", 0)) for d in detections]
        logger.info(f"📊 Total Objects Detected : {count}")
        logger.info(f"🕳  Total Potholes         : {count}")
        logger.info(f"📈 Highest Confidence     : {max(confs) * 100:.2f}%")
        logger.info(f"📉 Lowest Confidence      : {min(confs) * 100:.2f}%")
        logger.info(f"📐 Average Confidence     : {(sum(confs)/count) * 100:.2f}%")

    # ------------------------------------------------------------------
    # Image / storage
    # ------------------------------------------------------------------
    def image_saved(self):
        logger.info("🖼  Annotated image created successfully.")

    def upload_start(self):
        logger.info("☁  Uploading image to Supabase Storage...")

    def upload_done(self, url: str = None):
        logger.info("✅ Image uploaded successfully.")
        if url:
            logger.info(f"🔗 Image URL : {url}")

    # ------------------------------------------------------------------
    # Database
    # ------------------------------------------------------------------
    def db_saving(self):
        logger.info("💾 Saving report...")

    def db_done(self, report_id=None):
        logger.info("✅ Report inserted successfully.")
        if report_id is not None:
            logger.info(f"🆔 Report ID : {report_id}")

    # ------------------------------------------------------------------
    # Timings
    # ------------------------------------------------------------------
    def timings(
        self,
        *,
        yolo_ms: float = None,
        upload_ms: float = None,
        db_ms: float = None,
        total_s: float = None,
    ):
        if yolo_ms is not None:
            logger.info(f"⏱  YOLO Inference Time   : {yolo_ms:.0f} ms")
        if upload_ms is not None:
            logger.info(f"⏱  Upload Time           : {upload_ms:.0f} ms")
        if db_ms is not None:
            logger.info(f"⏱  Database Time         : {db_ms:.0f} ms")
        if total_s is not None:
            logger.info(f"⏱  Total Processing Time : {total_s:.2f} s")

    # ------------------------------------------------------------------
    # Error
    # ------------------------------------------------------------------
    def error(self, exc: Exception):
        tb = traceback.extract_tb(exc.__traceback__)
        last = tb[-1] if tb else None
        logger.error(f"❌ ERROR      : {exc}")
        if last:
            logger.error(f"📍 File       : {os.path.basename(last.filename)}")
            logger.error(f"📍 Function   : {last.name}")
            logger.error(f"📍 Line Number: {last.lineno}")
        logger.error(SEP)
