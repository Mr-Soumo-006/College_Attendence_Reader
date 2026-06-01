"""
Time utilities for the Smart Campus Attendance System.
"""

import zoneinfo
from datetime import datetime, timedelta
from config.settings import TIMEZONE, CLASS_START_TIME, LATE_THRESHOLD_MIN


def now() -> datetime:
    """Return the current datetime in the configured timezone."""
    return datetime.now(tz=zoneinfo.ZoneInfo(TIMEZONE))


def today_str() -> str:
    """Return today's date as YYYY-MM-DD string."""
    return now().strftime("%Y-%m-%d")


def time_slot(dt: datetime | None = None) -> str:
    """
    Return a rounded hour slot string like '09AM', '10AM', '02PM'.
    Used as part of the QR payload so codes expire hourly.
    """
    dt = dt or now()
    return dt.strftime("%I%p").lstrip("0")  # e.g. '09AM' -> '9AM'


def attendance_status() -> str:
    """
    Return 'ON TIME' or 'LATE' based on the current time vs CLASS_START_TIME.
    """
    current = now()
    h, m = map(int, CLASS_START_TIME.split(":"))
    class_start = current.replace(hour=h, minute=m, second=0, microsecond=0)
    cutoff = class_start + timedelta(minutes=LATE_THRESHOLD_MIN)
    if current <= cutoff:
        return "ON TIME"
    return "LATE"


def minutes_late() -> int:
    """
    Return how many minutes past the late-threshold the student is.
    Returns 0 if on time.
    """
    current = now()
    h, m = map(int, CLASS_START_TIME.split(":"))
    class_start = current.replace(hour=h, minute=m, second=0, microsecond=0)
    cutoff = class_start + timedelta(minutes=LATE_THRESHOLD_MIN)
    if current <= cutoff:
        return 0
    delta = int((current - cutoff).total_seconds() / 60)
    return max(0, delta)
