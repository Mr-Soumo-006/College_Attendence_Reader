"""
Console UI helpers — banners, coloured output, result cards.
"""

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich import box

console = Console()


def print_banner() -> None:
    banner = Text()
    banner.append("  Smart Campus Attendance System\n", style="bold cyan")
    banner.append("  QR + Face + Geo-Fence + ML Analytics\n", style="dim")
    console.print(Panel(banner, box=box.DOUBLE, border_style="cyan", padding=(0, 4)))


def print_scan_result(student: dict, status: str, minutes_late: int,
                      face_verified: bool, alerts: list[str]) -> None:
    status_style = {"ON TIME": "green", "LATE": "yellow", "ABSENT": "red"}.get(
        status, "white"
    )
    lines = [
        f"[bold cyan]{student['name']}[/]  ({student['student_id']})",
        f"Class: {student['class']}",
        f"Status: [{status_style}]{status}[/]" +
        (f"  (+{minutes_late} min)" if minutes_late else ""),
        f"Face verified: {'[green]YES[/]' if face_verified else '[yellow]SKIPPED[/]'}",
    ]
    if alerts:
        lines.append(f"[red]Alerts fired: {', '.join(alerts)}[/]")
    console.print(Panel("\n".join(lines), title="Attendance Marked",
                        border_style=status_style, box=box.ROUNDED))


def print_error(msg: str)   -> None: console.print(f"[bold red]ERROR:[/] {msg}")
def print_warning(msg: str) -> None: console.print(f"[bold yellow]WARNING:[/] {msg}")
def print_success(msg: str) -> None: console.print(f"[bold green]OK:[/] {msg}")
def print_info(msg: str)    -> None: console.print(f"[cyan]INFO:[/] {msg}")
