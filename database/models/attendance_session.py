"""
CRUD helpers for the `attendance_sessions` table.
"""

from datetime import datetime, timedelta
from database.connection import DBConnection


def create_session(session_name: str, teacher_id: str, duration_minutes: int) -> dict:
    """Insert a new session starting now and ending after the given duration."""
    start_time = datetime.now()
    end_time = start_time + timedelta(minutes=duration_minutes)
    
    # Deactivate any currently active sessions first to avoid duplicates
    end_active_session()
    
    with DBConnection() as (conn, cur):
        cur.execute(
            """INSERT INTO attendance_sessions (session_name, teacher_id, start_time, end_time, is_active)
               VALUES (%s, %s, %s, %s, 1)""",
            (session_name.strip(), teacher_id.strip().upper(), start_time, end_time),
        )
    return get_active_session()


def get_active_session() -> dict | None:
    """Retrieve the currently active session if one exists and hasn't expired."""
    now = datetime.now()
    with DBConnection() as (conn, cur):
        cur.execute(
            """SELECT id, session_name, teacher_id, start_time, end_time, is_active 
               FROM attendance_sessions 
               WHERE is_active = 1 AND end_time > %s
               ORDER BY created_at DESC LIMIT 1""",
            (now,),
        )
        session = cur.fetchone()
    
    # If a session exists but has technically expired, deactivate it automatically
    if not session:
        # Check if there are active sessions in the database that should be deactivated
        with DBConnection() as (conn, cur):
            cur.execute("UPDATE attendance_sessions SET is_active = 0 WHERE is_active = 1")
        return None
        
    return session


def end_active_session() -> None:
    """Manually end any currently active session."""
    with DBConnection() as (conn, cur):
        cur.execute("UPDATE attendance_sessions SET is_active = 0 WHERE is_active = 1")
