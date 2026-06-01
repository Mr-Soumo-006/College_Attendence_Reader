"""
Alert Engine
------------
Evaluates alert rules after every attendance mark and after analytics refresh.
Persists triggered alerts and optionally sends notifications.
"""

from database.models.attendance import get_history
from database.models.alert import create_alert, get_alert_count
from config.settings import ALERT_LATE_COUNT, ALERT_ABSENT_DAYS


def check_late_streak(student_id: str) -> bool:
    """Fire LATE_STREAK alert if student was late >= ALERT_LATE_COUNT times recently."""
    records = get_history(student_id, days=14)
    if not records:
        return False
    late_count = sum(1 for r in records if r["status"] == "LATE")
    if late_count >= ALERT_LATE_COUNT:
        existing = get_alert_count(student_id, "LATE_STREAK", last_n_days=1)
        if existing == 0:
            create_alert(
                student_id=student_id,
                alert_type="LATE_STREAK",
                severity="WARNING",
                message=(
                    f"Student has been late {late_count} times in the last 14 days. "
                    f"Threshold: {ALERT_LATE_COUNT}."
                ),
            )
            return True
    return False


def check_absent_streak(student_id: str) -> bool:
    """Fire ABSENT_STREAK alert if student has been absent ALERT_ABSENT_DAYS in a row."""
    records = get_history(student_id, days=ALERT_ABSENT_DAYS + 2)
    if not records:
        return False
    recent = [r["status"] for r in records[:ALERT_ABSENT_DAYS]]
    if all(s == "ABSENT" for s in recent):
        existing = get_alert_count(student_id, "ABSENT_STREAK", last_n_days=1)
        if existing == 0:
            create_alert(
                student_id=student_id,
                alert_type="ABSENT_STREAK",
                severity="CRITICAL",
                message=(
                    f"Student has been absent for {ALERT_ABSENT_DAYS} consecutive days!"
                ),
            )
            return True
    return False


def check_proxy_attempt(student_id: str) -> None:
    """Log a PROXY_ATTEMPT alert (called from hybrid_auth when face mismatch)."""
    create_alert(
        student_id=student_id,
        alert_type="PROXY_ATTEMPT",
        severity="CRITICAL",
        message=(
            f"Face mismatch detected for '{student_id}'. "
            "Possible proxy attendance attempt blocked."
        ),
    )


def check_geo_fence_violation(student_id: str, ip: str) -> None:
    """Log a GEO_FENCE alert."""
    create_alert(
        student_id=student_id,
        alert_type="GEO_FENCE",
        severity="CRITICAL",
        message=f"Attendance attempt from outside campus network (IP: {ip}).",
    )


def check_high_risk(student_id: str, risk_level: str) -> bool:
    """Fire RISK_HIGH alert when a student crosses into HIGH risk."""
    if risk_level != "HIGH":
        return False
    existing = get_alert_count(student_id, "RISK_HIGH", last_n_days=7)
    if existing == 0:
        create_alert(
            student_id=student_id,
            alert_type="RISK_HIGH",
            severity="WARNING",
            message="Student has been classified as HIGH attendance risk.",
        )
        return True
    return False


def run_all_checks(student_id: str, status: str) -> list[str]:
    """
    Run the full suite of post-attendance checks for *student_id*.
    Returns a list of alert types that were fired.
    """
    fired = []
    if check_late_streak(student_id):
        fired.append("LATE_STREAK")
    if check_absent_streak(student_id):
        fired.append("ABSENT_STREAK")

    from database.models.student import get_student
    try:
        student = get_student(student_id)
        if check_high_risk(student_id, student.get("risk_level", "LOW")):
            fired.append("RISK_HIGH")
    except Exception:
        pass

    return fired
