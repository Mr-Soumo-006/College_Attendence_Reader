"""
CRUD helpers for the `student_ratings` table.
"""

from database.connection import DBConnection


def submit_rating(student_id: str, teacher_id: str, subject: str, rating: int, comment: str) -> None:
    """Insert or update a student rating for a specific subject."""
    with DBConnection() as (conn, cur):
        cur.execute(
            """INSERT INTO student_ratings (student_id, teacher_id, subject, rating, comment)
               VALUES (%s, %s, %s, %s, %s)
               ON DUPLICATE KEY UPDATE
                   teacher_id = %s,
                   rating = %s,
                   comment = %s""",
            (student_id.strip().upper(), teacher_id.strip().upper(), subject.strip(), int(rating), comment.strip(),
             teacher_id.strip().upper(), int(rating), comment.strip()),
        )


def get_student_ratings(student_id: str) -> list[dict]:
    """Retrieve all subject-wise performance ratings and comments for *student_id*."""
    with DBConnection() as (conn, cur):
        cur.execute(
            """SELECT r.id, r.student_id, r.teacher_id, r.subject, r.rating, r.comment, r.created_at, t.name AS teacher_name
               FROM student_ratings r
               JOIN teachers t ON r.teacher_id = t.teacher_id
               WHERE r.student_id = %s
               ORDER BY r.subject""",
            (student_id.strip().upper(),),
        )
        return cur.fetchall()


def get_all_ratings() -> list[dict]:
    """Retrieve all student subject ratings with student and teacher name details."""
    with DBConnection() as (conn, cur):
        cur.execute(
            """SELECT r.id, r.student_id, r.teacher_id, r.subject, r.rating, r.comment, r.created_at, 
                      s.name AS student_name, t.name AS teacher_name
               FROM student_ratings r
               JOIN students s ON r.student_id = s.student_id
               JOIN teachers t ON r.teacher_id = t.teacher_id
               ORDER BY r.created_at DESC"""
        )
        return cur.fetchall()
