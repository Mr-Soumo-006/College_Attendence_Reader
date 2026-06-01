"""
CRUD helpers for the `attendance` table.
"""

from datetime import date, datetime
from database.connection import DBConnection
from utils.time_utils import today_str


def mark_attendance(student_id: str, status: str, minutes_late: int = 0,
                    ip_address: str = "", auth_method: str = "QR+FACE") -> dict:
    """Insert or update today's attendance for *student_id*. Returns the row."""
    today = today_str()
    now = datetime.now()
    with DBConnection() as (conn, cur):
        cur.execute(
            """INSERT INTO attendance
               (student_id, date, time_in, status, minutes_late, ip_address, auth_method)
               VALUES (%s,%s,%s,%s,%s,%s,%s)
               ON DUPLICATE KEY UPDATE
                   time_in=%s, status=%s, minutes_late=%s,
                   ip_address=%s, auth_method=%s""",
            (student_id, today, now, status, minutes_late, ip_address, auth_method,
             now, status, minutes_late, ip_address, auth_method),
        )
    return get_today_record(student_id)


def get_today_record(student_id: str) -> dict | None:
    with DBConnection() as (conn, cur):
        cur.execute(
            "SELECT * FROM attendance WHERE student_id=%s AND date=%s",
            (student_id, today_str()),
        )
        return cur.fetchone()


def get_history(student_id: str, days: int = 30) -> list[dict]:
    with DBConnection() as (conn, cur):
        cur.execute(
            """SELECT * FROM attendance
               WHERE student_id=%s
               ORDER BY date DESC LIMIT %s""",
            (student_id, days),
        )
        return cur.fetchall()


def get_all_today() -> list[dict]:
    with DBConnection() as (conn, cur):
        cur.execute(
            """SELECT a.*, s.name, s.class
               FROM attendance a
               JOIN students s ON a.student_id=s.student_id
               WHERE a.date=%s
               ORDER BY a.time_in""",
            (today_str(),),
        )
        return cur.fetchall()


def get_date_range(student_id: str, start: date, end: date) -> list[dict]:
    with DBConnection() as (conn, cur):
        cur.execute(
            """SELECT * FROM attendance
               WHERE student_id=%s AND date BETWEEN %s AND %s
               ORDER BY date""",
            (student_id, start.isoformat(), end.isoformat()),
        )
        return cur.fetchall()


def get_all_attendance_for_analytics() -> list[dict]:
    """Load full attendance table joined with student info for analytics."""
    with DBConnection() as (conn, cur):
        cur.execute(
            """SELECT a.*, s.name, s.class, s.risk_level
               FROM attendance a
               JOIN students s ON a.student_id=s.student_id
               ORDER BY a.student_id, a.date"""
        )
        return cur.fetchall()
