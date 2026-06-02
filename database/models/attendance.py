"""
CRUD helpers for the `attendance` table.
"""

from datetime import date, datetime
from database.connection import DBConnection
from utils.time_utils import today_str, now as get_now


def mark_attendance(student_id: str, status: str, minutes_late: int = 0,
                    ip_address: str = "", auth_method: str = "QR+FACE", device_id: str = "",
                    session_id: int = None) -> dict:
    """Insert or update attendance for *student_id* for a specific session. Returns the row."""
    today = today_str()
    now = get_now().replace(tzinfo=None)
    with DBConnection() as (conn, cur):
        cur.execute(
            """INSERT INTO attendance
               (student_id, date, time_in, status, minutes_late, ip_address, auth_method, device_id, session_id)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
               ON DUPLICATE KEY UPDATE
                   time_in=%s, status=%s, minutes_late=%s,
                   ip_address=%s, auth_method=%s, device_id=%s""",
            (student_id, today, now, status, minutes_late, ip_address, auth_method, device_id, session_id,
             now, status, minutes_late, ip_address, auth_method, device_id),
        )
    return get_session_record(student_id, session_id) if session_id else get_today_record(student_id)


def get_session_record(student_id: str, session_id: int) -> dict | None:
    """Retrieve attendance record for a specific student and session."""
    with DBConnection() as (conn, cur):
        cur.execute(
            "SELECT * FROM attendance WHERE student_id=%s AND session_id=%s LIMIT 1",
            (student_id, session_id),
        )
        return cur.fetchone()


def get_today_record(student_id: str) -> dict | None:
    with DBConnection() as (conn, cur):
        cur.execute(
            "SELECT * FROM attendance WHERE student_id=%s AND date=%s LIMIT 1",
            (student_id, today_str()),
        )
        return cur.fetchone()


def get_history(student_id: str, days: int = 30) -> list[dict]:
    with DBConnection() as (conn, cur):
        cur.execute(
            """SELECT a.*, s.session_name
               FROM attendance a
               LEFT JOIN attendance_sessions s ON a.session_id = s.id
               WHERE a.student_id=%s
               ORDER BY a.time_in DESC LIMIT %s""",
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


def mark_attendance_manual(student_id: str, date_str: str, status: str, session_id: int = None) -> None:
    """Insert or update a student's attendance record for a specific custom date."""
    status = status.upper().strip()
    assert status in ("ON TIME", "PRESENT", "LATE", "ABSENT")
    
    with DBConnection() as (conn, cur):
        # Delete any existing record for this student on this specific date/session
        if session_id:
            cur.execute(
                "DELETE FROM attendance WHERE student_id=%s AND session_id=%s",
                (student_id, session_id)
            )
        else:
            cur.execute(
                "DELETE FROM attendance WHERE student_id=%s AND date=%s",
                (student_id, date_str)
            )
        
        # Insert new record
        cur.execute(
            """INSERT INTO attendance 
               (student_id, date, time_in, status, minutes_late, ip_address, auth_method, session_id)
               VALUES (%s, %s, CURRENT_TIMESTAMP, %s, 0, '127.0.0.1', 'MANUAL', %s)""",
            (student_id.strip().upper(), date_str, status, session_id)
        )


def delete_attendance_record(student_id: str, date_str: str) -> None:
    """Remove a student's attendance record for a specific date."""
    with DBConnection() as (conn, cur):
        cur.execute(
            "DELETE FROM attendance WHERE student_id=%s AND date=%s",
            (student_id.strip().upper(), date_str)
        )
