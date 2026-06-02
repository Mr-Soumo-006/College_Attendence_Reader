"""
CRUD helpers for the `teachers` table.
"""

from werkzeug.security import generate_password_hash, check_password_hash
from database.connection import DBConnection


def create_teacher(teacher_id: str, name: str, email: str,
                   department: str, password: str) -> dict:
    """Insert a new teacher and return the row dict."""
    hashed_pw = generate_password_hash(password)
    with DBConnection() as (conn, cur):
        cur.execute(
            """INSERT INTO teachers (teacher_id, name, email, department, password)
               VALUES (%s, %s, %s, %s, %s)""",
            (teacher_id.strip().upper(), name.strip(), email.strip(),
             department.strip().upper(), hashed_pw),
        )
    return get_teacher(teacher_id)


def get_teacher(teacher_id: str) -> dict | None:
    """Retrieve a teacher by teacher_id."""
    with DBConnection() as (conn, cur):
        cur.execute(
            "SELECT id, teacher_id, name, email, department FROM teachers WHERE teacher_id=%s",
            (teacher_id.strip().upper(),),
        )
        return cur.fetchone()


def get_all_teachers() -> list[dict]:
    """Retrieve all teachers."""
    with DBConnection() as (conn, cur):
        cur.execute("SELECT id, teacher_id, name, email, department, created_at FROM teachers ORDER BY name")
        return cur.fetchall()


def verify_teacher_login(teacher_id: str, password: str) -> dict | None:
    """Verify credentials and return the teacher info if valid."""
    with DBConnection() as (conn, cur):
        cur.execute(
            "SELECT id, teacher_id, name, email, department, password FROM teachers WHERE teacher_id=%s",
            (teacher_id.strip().upper(),),
        )
        teacher = cur.fetchone()
    if teacher and check_password_hash(teacher["password"], password):
        # Remove password hash from dictionary before returning
        teacher.pop("password")
        return teacher
    return None


def delete_teacher(teacher_id: str) -> None:
    """Physically delete a teacher from the database."""
    with DBConnection() as (conn, cur):
        cur.execute(
            "DELETE FROM teachers WHERE teacher_id=%s",
            (teacher_id.strip().upper(),),
        )
