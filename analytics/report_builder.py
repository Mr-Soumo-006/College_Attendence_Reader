"""
Report Builder
--------------
Generates human-readable summary reports for the console dashboard.
"""

from analytics.metrics_engine import compute_all_stats, get_high_risk_students
from analytics.pattern_detector import trend_analysis, analyze_dow_pattern
from database.models.student import get_all_students
from utils.time_utils import today_str


def class_summary_report() -> dict:
    """
    Return a dict summarizing today's class attendance state.
    """
    from database.models.attendance import get_all_today
    today_records  = get_all_today()
    total_students = len(get_all_students())
    present = sum(1 for r in today_records if r["status"] != "ABSENT")
    late    = sum(1 for r in today_records if r["status"] == "LATE")
    absent  = total_students - present
    high_risk = get_high_risk_students()

    return {
        "date":            today_str(),
        "total_students":  total_students,
        "present":         present,
        "late":            late,
        "absent":          absent,
        "attendance_rate": round(present / total_students * 100, 1) if total_students else 0,
        "high_risk_count": len(high_risk),
    }


def student_report_card(student_id: str) -> dict:
    """Full report card for one student including trend and DOW pattern."""
    from analytics.metrics_engine import get_student_summary
    stats = get_student_summary(student_id)
    trend = trend_analysis(student_id)
    dow   = analyze_dow_pattern(student_id)

    worst_day = None
    if dow:
        worst_day = max(dow.items(), key=lambda kv: kv[1]["absent_pct"])[0]

    return {
        "stats":       stats,
        "trend":       trend,
        "dow_pattern": dow,
        "worst_day":   worst_day,
    }
