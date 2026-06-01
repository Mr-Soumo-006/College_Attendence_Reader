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
        cur.close()
        raw_conn.close()
    except mysql.connector.Error as exc:
        raise DatabaseError(f"Schema init failed: {exc}") from exc
