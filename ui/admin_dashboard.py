"""
Admin Dashboard — Rich console tables and panels.
"""

from rich.console import Console
from rich.table import Table
from rich import box
from rich.panel import Panel

console = Console()


def show_today_attendance() -> None:
    from database.models.attendance import get_all_today
    records = get_all_today()
    if not records:
        console.print("[yellow]No attendance records for today.[/]")
        return

    t = Table(title="Today's Attendance", box=box.ROUNDED, border_style="cyan")
    t.add_column("Student ID", style="cyan")
    t.add_column("Name")
    t.add_column("Class")
    t.add_column("Status")
    t.add_column("Time In")
    t.add_column("Minutes Late", justify="right")
    t.add_column("Auth")

    for r in records:
        status_style = {
            "ON TIME": "green",
            "LATE":    "yellow",
            "ABSENT":  "red",
        }.get(r["status"], "white")
        t.add_row(
            r["student_id"],
            r["name"],
            r["class"],
            f"[{status_style}]{r['status']}[/]",
            str(r["time_in"]),
            str(r.get("minutes_late", 0)),
            r.get("auth_method", ""),
        )
    console.print(t)


def show_analytics_overview() -> None:
    from analytics.metrics_engine import compute_all_stats
    records = compute_all_stats()
    if not records:
        console.print("[yellow]No analytics data available.[/]")
        return

    t = Table(title="Behavior Analytics", box=box.ROUNDED, border_style="magenta")
    t.add_column("Student ID", style="cyan")
    t.add_column("Name")
    t.add_column("Class")
    t.add_column("Total", justify="right")
    t.add_column("Absent%", justify="right")
    t.add_column("Late%", justify="right")
    t.add_column("Max Streak", justify="right")
    t.add_column("Risk")

    for row in records:
        risk_style = {"LOW": "green", "MEDIUM": "yellow", "HIGH": "red"}.get(
            row["risk_level"], "white"
        )
        t.add_row(
            row["student_id"],
            row["name"],
            row["class"],
            str(row["total_classes"]),
            f"{row['absent_pct']}%",
            f"{row['late_pct']}%",
            str(row["max_absent_streak"]),
            f"[{risk_style}]{row['risk_level']}[/]",
        )
    console.print(t)


def show_student_report(student_id: str) -> None:
    from analytics.report_builder import student_report_card
    card = student_report_card(student_id)
    if not card["stats"]:
        console.print(f"[yellow]No data found for {student_id}.[/]")
        return

    s = card["stats"]
    lines = [
        f"[cyan]Student:[/]  {student_id}",
        f"[cyan]Trend:[/]    {card['trend']}",
        f"[cyan]Worst Day:[/] {card.get('worst_day', 'N/A')}",
        f"[cyan]Absent%:[/]  {s.get('absent_pct', 0)}%",
        f"[cyan]Late%:[/]    {s.get('late_pct', 0)}%",
        f"[cyan]Risk:[/]     {s.get('risk_level', 'N/A')}",
    ]
    console.print(Panel("\n".join(lines), title="Student Report Card", border_style="cyan"))


def show_predictions() -> None:
    from ml_module.predictor import predict_all_students
    results = predict_all_students()
    if not results:
        console.print("[yellow]No predictions available. Train the model first.[/]")
        return

    t = Table(title="ML Risk Predictions", box=box.ROUNDED, border_style="blue")
    t.add_column("Student ID", style="cyan")
    t.add_column("Name")
    t.add_column("Class")
    t.add_column("Prediction")
    t.add_column("High Risk Prob%", justify="right")

    for r in results:
        pred_style = "red" if r["risk_prediction"] == "HIGH" else "green"
        t.add_row(
            r["student_id"],
            r.get("name", ""),
            r.get("class", ""),
            f"[{pred_style}]{r['risk_prediction']}[/]",
            f"{r['probability_high']}%",
        )
    console.print(t)


def show_class_summary() -> None:
    from analytics.report_builder import class_summary_report
    s = class_summary_report()
    lines = [
        f"[cyan]Date:[/]           {s['date']}",
        f"[green]Present:[/]        {s['present']}",
        f"[yellow]Late:[/]           {s['late']}",
        f"[red]Absent:[/]         {s['absent']}",
        f"[cyan]Attendance Rate:[/] {s['attendance_rate']}%",
        f"[red]High Risk:[/]      {s['high_risk_count']} students",
    ]
    console.print(Panel("\n".join(lines), title="Class Summary", border_style="green"))


def show_alerts() -> None:
    from database.models.alert import get_unread_alerts
    alerts = get_unread_alerts()
    if not alerts:
        console.print("[green]No unread alerts.[/]")
        return

    t = Table(title="Unread Alerts", box=box.ROUNDED, border_style="red")
    t.add_column("Student ID", style="cyan")
    t.add_column("Name")
    t.add_column("Type")
    t.add_column("Severity")
    t.add_column("Message")
    t.add_column("Triggered At")

    for a in alerts:
        sev_style = {"CRITICAL": "red", "WARNING": "yellow", "INFO": "blue"}.get(
            a["severity"], "white"
        )
        t.add_row(
            a["student_id"],
            a.get("name", ""),
            a["alert_type"],
            f"[{sev_style}]{a['severity']}[/]",
            a.get("message", "")[:60],
            str(a["triggered_at"]),
        )
    console.print(t)
