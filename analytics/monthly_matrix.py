"""
Subject-wise & Monthly Attendance Register Analytics.
Provides detailed grids of monthly check-ins and subject-by-subject statistics.
"""

import calendar
from datetime import date
from database.connection import DBConnection
from database.models.student import get_all_students

def get_student_subject_attendance(student_id: str) -> list[dict]:
    """Calculate the student's attendance statistics grouped by subject/session name."""
    with DBConnection() as (conn, cur):
        cur.execute(
            """SELECT a.status, s.session_name
               FROM attendance a
               JOIN attendance_sessions s ON a.session_id = s.id
               WHERE a.student_id = %s""",
            (student_id,),
        )
        records = cur.fetchall()

    if not records:
        return []

    # Process statistics per subject
    subjects = {}
    for r in records:
        subj = r.get("session_name") or "Manual/Other"
        if subj not in subjects:
            subjects[subj] = {"subject": subj, "total": 0, "present": 0, "late": 0, "absent": 0}
        
        subjects[subj]["total"] += 1
        status = r["status"]
        if status in ("ON TIME", "PRESENT"):
            subjects[subj]["present"] += 1
        elif status == "LATE":
            subjects[subj]["present"] += 1
            subjects[subj]["late"] += 1
        else:
            subjects[subj]["absent"] += 1

    # Convert to list and calculate percentages
    summary = []
    for s in subjects.values():
        total = s["total"]
        rate = round((s["present"] / total) * 100, 1) if total else 0.0
        summary.append({
            "subject": s["subject"],
            "total_classes": total,
            "present_count": s["present"],
            "late_count": s["late"],
            "absent_count": s["absent"],
            "attendance_rate": rate
        })
    
    return sorted(summary, key=lambda x: x["subject"])


def get_monthly_attendance_matrix(year: int, month: int) -> dict:
    """
    Generate a complete calendar grid of student check-in status for the selected month.
    Returns:
      {
        "days": [1, 2, ..., 31],
        "students": [
          {
            "student_id": "BCA_028",
            "name": "Soumo Naskar",
            "days": {1: "P", 2: "L", 3: "A", 4: "—"}
          }
        ]
      }
    """
    # Get number of days in the month
    num_days = calendar.monthrange(year, month)[1]
    days_list = list(range(1, num_days + 1))

    # Retrieve all students
    students = get_all_students()
    if not students:
        return {"days": days_list, "students": []}

    # Retrieve all attendance records for the selected month
    start_date = date(year, month, 1)
    end_date = date(year, month, num_days)
    
    with DBConnection() as (conn, cur):
        cur.execute(
            """SELECT student_id, date, status
               FROM attendance
               WHERE date BETWEEN %s AND %s""",
            (start_date.isoformat(), end_date.isoformat()),
        )
        records = cur.fetchall()

    # Map attendance by student and day
    attendance_map = {}
    for r in records:
        sid = r["student_id"]
        day_num = r["date"].day if isinstance(r["date"], date) else int(str(r["date"]).split("-")[2])
        status = r["status"]
        
        # Determine cell badge: P (Present/On Time), L (Late), A (Absent)
        badge = "—"
        if status in ("ON TIME", "PRESENT"):
            badge = "P"
        elif status == "LATE":
            badge = "L"
        elif status == "ABSENT":
            badge = "A"
            
        if sid not in attendance_map:
            attendance_map[sid] = {}
        attendance_map[sid][day_num] = badge

    # Compile the final student matrix
    student_matrix = []
    for s in students:
        sid = s["student_id"]
        row_days = {}
        for d in days_list:
            row_days[d] = attendance_map.get(sid, {}).get(d, "—")
            
        student_matrix.append({
            "student_id": sid,
            "name": s["name"],
            "class": s["class"],
            "days": row_days
        })

    return {
        "days": days_list,
        "students": sorted(student_matrix, key=lambda x: x["name"]),
        "year": year,
        "month": month,
        "month_name": calendar.month_name[month]
    }
