"""
Behavior Analytics Metrics Engine — Pure Python Edition.
Does not require pandas or numpy! Runs flawlessly on all Python versions (including 3.14.5).
"""

from database.models.attendance import get_all_attendance_for_analytics
from database.models.student import get_all_students, update_risk_level
from database.connection import DBConnection


def _risk(absent_pct: float, late_pct: float) -> str:
    if absent_pct > 40 or late_pct > 40:
        return "HIGH"
    if absent_pct > 20 or late_pct > 20:
        return "MEDIUM"
    return "LOW"


def compute_all_stats() -> list[dict]:
    """
    Build a list of dictionaries with one item per student containing:
      student_id, name, class, total_classes, present_count, late_count,
      absent_count, late_pct, absent_pct, avg_minutes_late,
      max_absent_streak, risk_level
    """
    rows = get_all_attendance_for_analytics()
    if not rows:
        return []

    # Group rows by student_id in pure Python
    grouped = {}
    for r in rows:
        sid = r["student_id"]
        if sid not in grouped:
            grouped[sid] = []
        grouped[sid].append(r)

    stats = []
    for sid, grp in grouped.items():
        # Sort group by date (which is a date object or string)
        grp = sorted(grp, key=lambda x: str(x["date"]))
        
        total = len(grp)
        present = sum(1 for x in grp if x["status"] != "ABSENT")
        late_cnt = sum(1 for x in grp if x["status"] == "LATE")
        absent_cnt = sum(1 for x in grp if x["status"] == "ABSENT")

        late_pct = round(late_cnt / total * 100, 1) if total else 0.0
        absent_pct = round(absent_cnt / total * 100, 1) if total else 0.0

        # Calculate average minutes late
        late_minutes_list = [x["minutes_late"] for x in grp if x["status"] == "LATE" and x["minutes_late"] is not None]
        avg_late = round(sum(late_minutes_list) / len(late_minutes_list), 1) if late_minutes_list else 0.0

        streak = _max_absent_streak([x["status"] for x in grp])
        risk = _risk(absent_pct, late_pct)

        stats.append({
            "student_id":        sid,
            "name":              grp[0]["name"],
            "class":             grp[0]["class"],
            "total_classes":     total,
            "present_count":     present,
            "late_count":        late_cnt,
            "absent_count":      absent_cnt,
            "late_pct":          late_pct,
            "absent_pct":        absent_pct,
            "avg_minutes_late":  avg_late,
            "max_absent_streak": streak,
            "risk_level":        risk,
        })

    return stats


def _max_absent_streak(statuses: list[str]) -> int:
    """Return the length of the longest consecutive absent run."""
    max_s, cur_s = 0, 0
    for s in statuses:
        if s == "ABSENT":
            cur_s += 1
            max_s = max(max_s, cur_s)
        else:
            cur_s = 0
    return max_s


def refresh_behavior_stats() -> None:
    """
    Recompute all student stats and write to behavior_stats table.
    Also updates risk_level on the students table.
    """
    stats = compute_all_stats()
    if not stats:
        return

    with DBConnection() as (conn, cur):
        for s in stats:
            cur.execute(
                """INSERT INTO behavior_stats
                   (student_id, total_classes, present_count, late_count,
                    absent_count, late_pct, absent_pct, avg_minutes_late,
                    max_absent_streak, risk_level)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                   ON DUPLICATE KEY UPDATE
                     total_classes=%s, present_count=%s, late_count=%s,
                     absent_count=%s, late_pct=%s, absent_pct=%s,
                     avg_minutes_late=%s, max_absent_streak=%s, risk_level=%s""",
                (
                    s["student_id"],
                    s["total_classes"], s["present_count"], s["late_count"],
                    s["absent_count"], s["late_pct"], s["absent_pct"],
                    s["avg_minutes_late"], s["max_absent_streak"], s["risk_level"],
                    s["total_classes"], s["present_count"], s["late_count"],
                    s["absent_count"], s["late_pct"], s["absent_pct"],
                    s["avg_minutes_late"], s["max_absent_streak"], s["risk_level"],
                ),
            )

    for s in stats:
        update_risk_level(s["student_id"], s["risk_level"])


def get_student_summary(student_id: str) -> dict | None:
    """Return cached behavior stats for a single student."""
    with DBConnection() as (conn, cur):
        cur.execute(
            "SELECT * FROM behavior_stats WHERE student_id=%s",
            (student_id,),
        )
        return cur.fetchone()


def get_high_risk_students() -> list[dict]:
    with DBConnection() as (conn, cur):
        cur.execute(
            """SELECT bs.*, s.name, s.class, s.email
               FROM behavior_stats bs
               JOIN students s ON bs.student_id=s.student_id
               WHERE bs.risk_level='HIGH'
               ORDER BY bs.absent_pct DESC"""
        )
        return cur.fetchall()
