"""
Pattern Detector — Pure Python Edition.
Identifies behavioral patterns like DOW trends, window trends, and anomalies.
Works on all Python versions (including 3.14.5) with zero dependencies!
"""

import math
from datetime import datetime
from database.models.attendance import get_history


def analyze_dow_pattern(student_id: str, days: int = 60) -> dict:
    """
    Return per-day-of-week absence and late rates for *student_id*.
    e.g. {"Monday": {"absent_pct": 60.0, "late_pct": 20.0}, ...}
    """
    records = get_history(student_id, days=days)
    if not records:
        return {}

    # Group by day name
    grouped = {}
    for r in records:
        # Convert date to datetime if it's a string, or format if it's a date/datetime
        dt = r["date"]
        if isinstance(dt, str):
            dt_obj = datetime.strptime(dt, "%Y-%m-%d")
        else:
            # Assumed to be a date/datetime object
            dt_obj = datetime(dt.year, dt.month, dt.day)
            
        day_name = dt_obj.strftime("%A")
        if day_name not in grouped:
            grouped[day_name] = []
        grouped[day_name].append(r)

    result = {}
    for day, grp in grouped.items():
        total = len(grp)
        absent_cnt = sum(1 for x in grp if x["status"] == "ABSENT")
        late_cnt = sum(1 for x in grp if x["status"] == "LATE")
        result[day] = {
            "absent_pct": round(absent_cnt / total * 100, 1),
            "late_pct":   round(late_cnt   / total * 100, 1),
            "total":      total,
        }
    return result


def trend_analysis(student_id: str, window: int = 14) -> str:
    """
    Compare attendance in the last *window* days vs the previous *window* days.
    Returns: 'IMPROVING', 'WORSENING', or 'STABLE'
    """
    records = get_history(student_id, days=window * 2)
    if len(records) < window:
        return "STABLE"

    # Sort ascending by date
    sorted_records = sorted(records, key=lambda x: str(x["date"]))

    older = sorted_records[:window]
    recent = sorted_records[window:]

    def attendance_score(d_list: list[dict]) -> float:
        if not d_list:
            return 0.0
        on_time = sum(1 for x in d_list if x["status"] == "ON TIME")
        return on_time / len(d_list)

    recent_score = attendance_score(recent)
    older_score  = attendance_score(older)

    if recent_score > older_score + 0.1:
        return "IMPROVING"
    if recent_score < older_score - 0.1:
        return "WORSENING"
    return "STABLE"


def detect_anomalies_zscore(stats_list: list[dict],
                             column: str = "absent_pct",
                             threshold: float = 2.0) -> list[str]:
    """
    Return student_ids whose *column* value is > *threshold* standard
    deviations above the class mean (Z-score outlier detection).
    """
    if not stats_list:
        return []
        
    values = [s[column] for s in stats_list if column in s]
    if not values:
        return []
        
    n = len(values)
    mean = sum(values) / n
    
    # Calculate standard deviation
    variance = sum((x - mean) ** 2 for x in values) / n
    std = math.sqrt(variance)
    
    if std == 0:
        return []
        
    anomalies = []
    for s in stats_list:
        if column in s:
            val = s[column]
            z_score = (val - mean) / std
            if z_score > threshold:
                anomalies.append(s["student_id"])
                
    return anomalies
