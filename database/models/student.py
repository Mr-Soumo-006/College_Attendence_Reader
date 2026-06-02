"""
CRUD helpers for the `students` table.
"""

import json
import uuid
from typing import Optional
from database.connection import DBConnection
from utils.exceptions import StudentNotFoundError


def create_student(student_id: str, name: str, department: str, year: int, semester: int,
                   email: str = "", phone: str = "") -> dict:
    """Insert a new student and return the row dict."""
    seed = uuid.uuid4().hex  # unique per-student QR seed
    class_ = f"{department.strip().upper()} (Year {year}, Sem {semester})"
    with DBConnection() as (conn, cur):
        cur.execute(
            """INSERT INTO students
               (student_id, name, class, email, phone, qr_seed, department, year, semester)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (student_id.strip().upper(), name.strip(), class_, email.strip(),
             phone.strip(), seed, department.strip().upper(), int(year), int(semester)),
        )
    return get_student(student_id)


def get_student(student_id: str) -> dict:
    with DBConnection() as (conn, cur):
        cur.execute(
            "SELECT * FROM students WHERE student_id=%s AND is_active=1",
            (student_id,),
        )
        row = cur.fetchone()
    if not row:
        raise StudentNotFoundError(f"Student '{student_id}' not found.")
    return row


def get_all_students() -> list[dict]:
    with DBConnection() as (conn, cur):
        cur.execute("SELECT * FROM students WHERE is_active=1 ORDER BY name")
        return cur.fetchall()


def update_face_encoding(student_id: str, encoding: list[float]) -> None:
    with DBConnection() as (conn, cur):
        cur.execute(
            "UPDATE students SET face_encoding=%s WHERE student_id=%s",
            (json.dumps(encoding), student_id),
        )


def update_risk_level(student_id: str, level: str) -> None:
    level = level.upper()
    assert level in ("LOW", "MEDIUM", "HIGH")
    with DBConnection() as (conn, cur):
        cur.execute(
            "UPDATE students SET risk_level=%s WHERE student_id=%s",
            (level, student_id),
        )


def get_face_encoding(student_id: str) -> Optional[list[float]]:
    row = get_student(student_id)
    raw = row.get("face_encoding")
    if raw is None:
        return None
    return json.loads(raw)


def deactivate_student(student_id: str) -> None:
    with DBConnection() as (conn, cur):
        cur.execute(
            "UPDATE students SET is_active=0 WHERE student_id=%s",
            (student_id,),
        )


def delete_student(student_id: str) -> None:
    """Physically delete a student from the database."""
    with DBConnection() as (conn, cur):
        cur.execute(
            "DELETE FROM students WHERE student_id=%s",
            (student_id,),
        )
