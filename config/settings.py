"""
Central configuration loader.
Reads from .env file and exposes typed settings to all modules.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env", override=False)

# ── Database ──────────────────────────────────────────────────
DB_HOST     = os.getenv("DB_HOST", "localhost")
DB_PORT     = int(os.getenv("DB_PORT", "3306"))
DB_NAME     = os.getenv("DB_NAME", "smart_campus")
DB_USER     = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

# ── Security ──────────────────────────────────────────────────
QR_SECRET_KEY       = os.getenv("QR_SECRET_KEY", "DEFAULT_SECRET_CHANGE_ME_32CHARS")
QR_VALIDITY_MINUTES = int(os.getenv("QR_VALIDITY_MINUTES", "60"))

# ── Camera / Face ─────────────────────────────────────────────
CAMERA_INDEX   = int(os.getenv("CAMERA_INDEX", "0"))
FACE_TOLERANCE = float(os.getenv("FACE_TOLERANCE", "0.5"))

# ── Geo-fencing ───────────────────────────────────────────────
ALLOWED_IP_PREFIXES = [
    p.strip() for p in
    os.getenv("ALLOWED_IP_PREFIXES", "192.168.1.,10.0.0.,127.0.0.1").split(",")
    if p.strip()
]

COLLEGE_LAT = float(os.getenv("COLLEGE_LAT", "22.448376236684407"))
COLLEGE_LNG = float(os.getenv("COLLEGE_LNG", "88.4143063288526"))
GEOFENCE_RADIUS_METERS = float(os.getenv("GEOFENCE_RADIUS_METERS", "500"))

# ── Class Schedule ────────────────────────────────────────────
CLASS_START_TIME   = os.getenv("CLASS_START_TIME", "09:00")   # HH:MM
LATE_THRESHOLD_MIN = int(os.getenv("LATE_THRESHOLD_MINUTES", "15"))

# ── Alerts ────────────────────────────────────────────────────
ALERT_LATE_COUNT  = int(os.getenv("ALERT_LATE_COUNT", "3"))
ALERT_ABSENT_DAYS = int(os.getenv("ALERT_ABSENT_DAYS", "3"))
EMAIL_ENABLED     = os.getenv("EMAIL_ENABLED", "false").lower() == "true"
EMAIL_SMTP        = os.getenv("EMAIL_SMTP", "smtp.gmail.com")
EMAIL_PORT        = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USER        = os.getenv("EMAIL_USER", "")
EMAIL_PASSWORD    = os.getenv("EMAIL_PASSWORD", "")

# ── ML ────────────────────────────────────────────────────────
MIN_TRAINING_RECORDS  = int(os.getenv("MIN_TRAINING_RECORDS", "10"))
RETRAIN_INTERVAL_DAYS = int(os.getenv("RETRAIN_INTERVAL_DAYS", "7"))

# ── System ────────────────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
TIMEZONE  = os.getenv("TIMEZONE", "Asia/Kolkata")

# ── Paths ─────────────────────────────────────────────────────
DATA_DIR      = _ROOT / "data"
FACES_DIR     = DATA_DIR / "student_faces"
QR_CODES_DIR  = DATA_DIR / "qr_codes"
LOGS_DIR      = _ROOT / "logs"
ML_MODELS_DIR = _ROOT / "ml_module" / "saved_models"

for _dir in (DATA_DIR, FACES_DIR, QR_CODES_DIR, LOGS_DIR, ML_MODELS_DIR):
    _dir.mkdir(parents=True, exist_ok=True)
