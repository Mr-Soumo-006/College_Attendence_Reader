"""
MySQL connection manager.
Provides a context manager that returns a connection from the pool.
"""

import mysql.connector
from mysql.connector import pooling
from config import settings
from utils.exceptions import DatabaseError

_pool: pooling.MySQLConnectionPool | None = None


def _get_pool() -> pooling.MySQLConnectionPool:
    global _pool
    if _pool is None:
        try:
            _pool = pooling.MySQLConnectionPool(
                pool_name="smart_campus_pool",
                pool_size=5,
                host=settings.DB_HOST,
                port=settings.DB_PORT,
                database=settings.DB_NAME,
                user=settings.DB_USER,
                password=settings.DB_PASSWORD,
                charset="utf8mb4",
                autocommit=False,
            )
        except mysql.connector.Error as exc:
            raise DatabaseError(f"Cannot create MySQL pool: {exc}") from exc
    return _pool


class DBConnection:
    """Context manager that yields (connection, cursor) and auto-commits or rolls back."""

    def __init__(self, dictionary: bool = True):
        self._dictionary = dictionary
        self._conn = None
        self._cur = None

    def __enter__(self):
        try:
            self._conn = _get_pool().get_connection()
            self._cur = self._conn.cursor(dictionary=self._dictionary)
            return self._conn, self._cur
        except mysql.connector.Error as exc:
            raise DatabaseError(str(exc)) from exc

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self._conn.commit()
        else:
            self._conn.rollback()
        self._cur.close()
        self._conn.close()
        return False  # re-raise exceptions


def init_db() -> None:
    """Create all tables by running schema.sql against the configured database."""
    import pathlib
    schema_path = pathlib.Path(__file__).parent / "schema.sql"
    sql_text = schema_path.read_text(encoding="utf-8")

    # mysql-connector does not support multi-statement execute directly;
    # split on semicolons and run each statement.
    try:
        raw_conn = mysql.connector.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            charset="utf8mb4",
        )
        cur = raw_conn.cursor()
        for stmt in sql_text.split(";"):
            stmt = stmt.strip()
            if stmt:
                try:
                    cur.execute(stmt)
                except mysql.connector.Error:
                    pass  # skip already-existing objects
        raw_conn.commit()
        # Ensure existing database has the 'GPS' option in the auth_method enum
        try:
            cur.execute("USE smart_campus")
            cur.execute("ALTER TABLE attendance MODIFY COLUMN auth_method ENUM('QR','QR+FACE','MANUAL','GPS') DEFAULT 'QR+FACE'")
            raw_conn.commit()
        except mysql.connector.Error:
            pass

        # Ensure existing students table has the department, year, and semester columns
        try:
            cur.execute("USE smart_campus")
            cur.execute("ALTER TABLE students ADD COLUMN department VARCHAR(50) NOT NULL DEFAULT 'BCA'")
            raw_conn.commit()
        except mysql.connector.Error:
            pass

        try:
            cur.execute("USE smart_campus")
            cur.execute("ALTER TABLE students ADD COLUMN year INT NOT NULL DEFAULT 1")
            raw_conn.commit()
        except mysql.connector.Error:
            pass

        try:
            cur.execute("USE smart_campus")
            cur.execute("ALTER TABLE students ADD COLUMN semester INT NOT NULL DEFAULT 1")
            raw_conn.commit()
        except mysql.connector.Error:
            pass

        # Alter department column to VARCHAR(50) in students and teachers tables
        try:
            cur.execute("USE smart_campus")
            cur.execute("ALTER TABLE students MODIFY COLUMN department VARCHAR(50) NOT NULL")
            cur.execute("ALTER TABLE teachers MODIFY COLUMN department VARCHAR(50) NOT NULL")
            raw_conn.commit()
        except mysql.connector.Error:
            pass

        # Seed default teacher T101 / admin123 if teachers table is empty
        try:
            cur.execute("USE smart_campus")
            cur.execute("SELECT COUNT(*) FROM teachers")
            count = cur.fetchone()[0]
            if count == 0:
                from werkzeug.security import generate_password_hash
                hashed_pw = generate_password_hash("admin123")
                cur.execute(
                    """INSERT INTO teachers (teacher_id, name, email, department, password)
                       VALUES (%s, %s, %s, %s, %s)""",
                    ("T101", "Admin Teacher", "teacher@college.edu", "BCA", hashed_pw)
                )
                raw_conn.commit()
        except mysql.connector.Error:
            pass

        # Upgrade legacy SHA-256 hashes to secure werkzeug hashes
        try:
            cur.execute("USE smart_campus")
            from werkzeug.security import generate_password_hash
            # For default teacher T101
            cur.execute("SELECT password FROM teachers WHERE teacher_id = 'T101'")
            row = cur.fetchone()
            if row and row[0] == "240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9":
                hashed = generate_password_hash("admin123")
                cur.execute("UPDATE teachers SET password = %s WHERE teacher_id = 'T101'", (hashed,))
                raw_conn.commit()
            
            # For test teacher T102
            cur.execute("SELECT password FROM teachers WHERE teacher_id = 'T102'")
            row = cur.fetchone()
            if row and row[0] == "95d30169a59c418b52013315fc81bc99fdf0a7b03a116f346ab628496f349ed5":
                hashed = generate_password_hash("secretpassword")
                cur.execute("UPDATE teachers SET password = %s WHERE teacher_id = 'T102'", (hashed,))
                raw_conn.commit()
        except mysql.connector.Error:
            pass

        # Ensure the attendance_sessions and student_ratings tables are created
        try:
            cur.execute("USE smart_campus")
            cur.execute(
                """CREATE TABLE IF NOT EXISTS attendance_sessions (
                    id           INT          AUTO_INCREMENT PRIMARY KEY,
                    session_name VARCHAR(100) NOT NULL,
                    teacher_id   VARCHAR(20)  NOT NULL,
                    start_time   DATETIME     NOT NULL,
                    end_time     DATETIME     NOT NULL,
                    is_active    TINYINT(1)   DEFAULT 1,
                    created_at   DATETIME     DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (teacher_id) REFERENCES teachers(teacher_id) ON DELETE CASCADE
                )"""
            )
            cur.execute(
                """CREATE TABLE IF NOT EXISTS student_ratings (
                    id           INT          AUTO_INCREMENT PRIMARY KEY,
                    student_id   VARCHAR(20)  NOT NULL,
                    teacher_id   VARCHAR(20)  NOT NULL,
                    subject      VARCHAR(100) NOT NULL,
                    rating       INT          NOT NULL,
                    comment      TEXT,
                    created_at   DATETIME     DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
                    FOREIGN KEY (teacher_id) REFERENCES teachers(teacher_id) ON DELETE CASCADE,
                    UNIQUE KEY uq_student_subject (student_id, subject)
                )"""
            )
            raw_conn.commit()
        except mysql.connector.Error:
            pass

        # Ensure existing students table has device_id column for proxy protection
        try:
            cur.execute("USE smart_campus")
            cur.execute("ALTER TABLE students ADD COLUMN device_id VARCHAR(100) DEFAULT NULL")
            raw_conn.commit()
        except mysql.connector.Error:
            pass

        # Ensure attendance table has session_id column
        try:
            cur.execute("USE smart_campus")
            cur.execute("ALTER TABLE attendance ADD COLUMN session_id INT DEFAULT NULL")
            raw_conn.commit()
        except mysql.connector.Error:
            pass

        # Add foreign key linking attendance.session_id to attendance_sessions.id
        try:
            cur.execute("USE smart_campus")
            cur.execute("ALTER TABLE attendance ADD CONSTRAINT fk_attendance_session FOREIGN KEY (session_id) REFERENCES attendance_sessions(id) ON DELETE CASCADE")
            raw_conn.commit()
        except mysql.connector.Error:
            pass

        # Drop legacy unique daily constraint
        try:
            cur.execute("USE smart_campus")
            cur.execute("ALTER TABLE attendance DROP INDEX uq_student_date")
            raw_conn.commit()
        except mysql.connector.Error:
            pass

        # Add unique session constraint to allow multiple check-ins per day for different subjects
        try:
            cur.execute("USE smart_campus")
            cur.execute("ALTER TABLE attendance ADD UNIQUE KEY uq_student_session (student_id, session_id)")
            raw_conn.commit()
        except mysql.connector.Error:
            pass

        # Ensure attendance_sessions table has late_threshold column
        try:
            cur.execute("USE smart_campus")
            cur.execute("ALTER TABLE attendance_sessions ADD COLUMN late_threshold INT DEFAULT 10")
            raw_conn.commit()
        except mysql.connector.Error:
            pass

        cur.close()
        raw_conn.close()
    except mysql.connector.Error as exc:
        raise DatabaseError(f"Schema init failed: {exc}") from exc
