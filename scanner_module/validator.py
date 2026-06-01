"""
QR Code Validator
-----------------
Parses and validates the payload encoded in a scanned QR code.
Raises QRExpiredError or QRInvalidError on failure.
"""

from datetime import datetime, timedelta
import zoneinfo
from database.models.student import get_student
from utils.crypto import verify
from utils.time_utils import now, time_slot, today_str
from utils.exceptions import QRExpiredError, QRInvalidError, StudentNotFoundError
from config.settings import QR_VALIDITY_MINUTES, TIMEZONE


def parse_payload(raw: str) -> dict:
    """
    Parse raw QR string into components.
    Expected format: STU_101|2026-04-01|09AM|ABCD1234EFGH5678
    """
    parts = raw.strip().split("|")
    if len(parts) != 4:
        raise QRInvalidError(f"Malformed QR payload: expected 4 fields, got {len(parts)}")
    return {
        "student_id": parts[0],
        "date":       parts[1],
        "slot":       parts[2],
        "signature":  parts[3],
    }


def validate_qr(raw: str) -> dict:
    """
    Fully validate a QR payload.
    Returns the student dict on success.
    Raises QRInvalidError, QRExpiredError, or StudentNotFoundError.
    """
    parsed     = parse_payload(raw)
    student_id = parsed["student_id"]
    date_str   = parsed["date"]
    slot       = parsed["slot"]
    signature  = parsed["signature"]

    # 1. Student must exist
    student = get_student(student_id)

    # 2. Reconstruct expected payload and verify HMAC
    raw_payload = f"{student_id}|{date_str}|{slot}|{student['qr_seed']}"
    if not verify(raw_payload, signature):
        raise QRInvalidError("QR signature mismatch — possible fake or tampered code.")

    # 3. Check date freshness
    today = today_str()
    if date_str != today:
        raise QRExpiredError(f"QR is from {date_str}, today is {today}.")

    # 4. Check time-slot window
    try:
        tz       = zoneinfo.ZoneInfo(TIMEZONE)
        slot_dt  = datetime.strptime(f"{date_str} {slot}", "%Y-%m-%d %I%p").replace(tzinfo=tz)
        if now() - slot_dt > timedelta(minutes=QR_VALIDITY_MINUTES):
            raise QRExpiredError(
                f"QR slot '{slot}' expired (validity: {QR_VALIDITY_MINUTES} min)."
            )
    except ValueError:
        pass  # non-standard slot string — rely on date check above

    return student
