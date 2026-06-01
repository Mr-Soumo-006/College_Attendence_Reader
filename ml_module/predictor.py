"""
ML Predictor — Pure Python expert scoring system.
Generates real-time risk predictions using mathematical weighting.
Does not require numpy, pandas, joblib, or scikit-learn!
"""

from datetime import datetime, timedelta
from database.models.attendance import get_history
from database.connection import DBConnection


def _alert_count(student_id: str, days: int = 30) -> int:
    with DBConnection() as (conn, cur):
        cur.execute(
            """SELECT COUNT(*) as cnt FROM alerts
               WHERE student_id=%s
               AND triggered_at >= DATE_SUB(NOW(), INTERVAL %s DAY)""",
            (student_id, days),
        )
        row = cur.fetchone()
        return row["cnt"] if row else 0


def predict_student_risk(student_id: str) -> dict:
    """
    Predict the risk level for a single student mathematically.

    Returns:
    {
      "student_id": "STU_101",
      "risk_prediction": "HIGH" | "LOW",
      "probability_high": float,
      "features": {...}
    }
    """
    records = get_history(student_id, days=60)
    if not records:
        return {
            "student_id":       student_id,
            "risk_prediction":  "UNKNOWN",
            "probability_high": 0.0,
            "features":         {},
        }

    # Sort records by date ascending
    sorted_records = sorted(records, key=lambda x: str(x["date"]))

    # Find maximum date
    max_date_str = max(str(r["date"]) for r in sorted_records)
    max_date = datetime.strptime(max_date_str, "%Y-%m-%d")

    # Filter last 30 days
    recent = []
    for r in sorted_records:
        r_date = r["date"]
        if isinstance(r_date, str):
            r_dt = datetime.strptime(r_date, "%Y-%m-%d")
        else:
            r_dt = datetime(r_date.year, r_date.month, r_date.day)
            
        if max_date - r_dt <= timedelta(days=30):
            recent.append(r)

    total = len(recent)
    if total == 0:
        absent_pct = late_pct = avg_late = 0.0
    else:
        absent_cnt = sum(1 for x in recent if x["status"] == "ABSENT")
        late_cnt = sum(1 for x in recent if x["status"] == "LATE")
        absent_pct = absent_cnt / total * 100
        late_pct   = late_cnt   / total * 100
        
        late_minutes = [x["minutes_late"] for x in recent if x["status"] == "LATE" and x["minutes_late"] is not None]
        avg_late   = sum(late_minutes) / len(late_minutes) if late_minutes else 0.0

    # Calculate max absent streak
    streak, cur_s = 0, 0
    for r in sorted_records:
        s = r["status"]
        cur_s  = (cur_s + 1) if s == "ABSENT" else 0
        streak = max(streak, cur_s)

    # Group by day name to get Monday and Friday stats
    monday_records = []
    friday_records = []
    for r in sorted_records:
        dt = r["date"]
        if isinstance(dt, str):
            dt_obj = datetime.strptime(dt, "%Y-%m-%d")
        else:
            dt_obj = datetime(dt.year, dt.month, dt.day)
            
        day_name = dt_obj.strftime("%A")
        if day_name == "Monday":
            monday_records.append(r)
        elif day_name == "Friday":
            friday_records.append(r)

    mon_absent = (sum(1 for x in monday_records if x["status"] == "ABSENT") / len(monday_records) * 100) if monday_records else 0.0
    fri_absent = (sum(1 for x in friday_records if x["status"] == "ABSENT") / len(friday_records) * 100) if friday_records else 0.0

    trend = 0
    if len(sorted_records) >= 28:
        # Last 14 records vs older 14 records
        recent_14 = sorted_records[-14:]
        older_14 = sorted_records[-28:-14]
        rs = sum(1 for x in recent_14 if x["status"] == "ON TIME") / 14
        os_ = sum(1 for x in older_14 if x["status"] == "ON TIME") / 14
        trend = 1 if rs > os_ + 0.1 else (-1 if rs < os_ - 0.1 else 0)

    alerts = _alert_count(student_id)

    features = {
        "absent_pct_30d":       round(absent_pct, 1),
        "late_pct_30d":         round(late_pct, 1),
        "avg_minutes_late_30d": round(avg_late, 1),
        "max_absent_streak":    streak,
        "monday_absent_pct":    round(mon_absent, 1),
        "friday_absent_pct":    round(fri_absent, 1),
        "trend_score":          trend,
        "total_alerts":         alerts,
    }

    # Pure Python mathematical risk score (expert weighting)
    # High absence is weighted heaviest, followed by streaks, alerts, and lateness
    score = (absent_pct * 1.0) + (late_pct * 0.4) + (streak * 8.0) + (alerts * 10.0)
    # Factor in negative trend
    if trend == -1:
        score += 15.0
    elif trend == 1:
        score -= 10.0

    high_prob = min(max(score, 0.0), 100.0)
    pred = "HIGH" if high_prob >= 40.0 else "LOW"

    return {
        "student_id":       student_id,
        "risk_prediction":  pred,
        "probability_high": round(high_prob, 1),
        "features":         features,
    }


def predict_all_students() -> list[dict]:
    """Run predictions for every active student."""
    from database.models.student import get_all_students
    students = get_all_students()
    results  = []
    for s in students:
        try:
            r         = predict_student_risk(s["student_id"])
            r["name"]  = s["name"]
            r["class"] = s["class"]
            results.append(r)
        except Exception:
            pass
    return sorted(results, key=lambda x: x["probability_high"], reverse=True)
