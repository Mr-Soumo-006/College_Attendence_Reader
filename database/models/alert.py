"""
CRUD helpers for the `alerts` table.
"""

from database.connection import DBConnection


def create_alert(student_id: str, alert_type: str, message: str,
                 severity: str = "WARNING") -> None:
    with DBConnection() as (conn, cur):
        cur.execute(
            """INSERT INTO alerts (student_id, alert_type, severity, message)
               VALUES (%s,%s,%s,%s)""",
            (student_id, alert_type, severity, message),
        )


def get_unread_alerts(limit: int = 50) -> list[dict]:
    with DBConnection() as (conn, cur):
        cur.execute(
            """SELECT a.*, s.name
               FROM alerts a JOIN students s ON a.student_id=s.student_id
               WHERE a.is_read=0
               ORDER BY a.triggered_at DESC LIMIT %s""",
            (limit,),
        )
        return cur.fetchall()


def mark_alerts_read(student_id: str) -> None:
    with DBConnection() as (conn, cur):
        cur.execute(
            "UPDATE alerts SET is_read=1 WHERE student_id=%s",
            (student_id,),
        )


def get_alert_count(student_id: str, alert_type: str,
                    last_n_days: int = 7) -> int:
    with DBConnection() as (conn, cur):
        cur.execute(
            """SELECT COUNT(*) AS cnt FROM alerts
               WHERE student_id=%s AND alert_type=%s
               AND triggered_at >= DATE_SUB(NOW(), INTERVAL %s DAY)""",
            (student_id, alert_type, last_n_days),
        )
        row = cur.fetchone()
        return row["cnt"] if row else 0
