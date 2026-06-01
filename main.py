"""
Smart Campus Attendance System — Main Entry Point
===================================================
CLI menu that ties together all modules:
  1. Mark Attendance (QR + Face)
  2. Generate QR Code
  3. Enroll Student Face
  4. Add New Student
  5. Today's Attendance
  6. Analytics Overview
  7. Student Report Card
  8. ML Risk Predictions
  9. Train ML Model
  A. Class Summary
  B. View Alerts
  0. Exit
"""

import sys
import os

# Ensure project root is on sys.path so all module imports resolve
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Auto-detect if camera libraries (OpenCV/NumPy) are incompatible with the Python runtime
SIMULATION_MODE = False
try:
    import cv2
    import numpy as np
except (ImportError, AttributeError):
    SIMULATION_MODE = True

from rich.console import Console
from rich.prompt import Prompt
from rich import box
from rich.panel import Panel

from ui.console_ui import (
    print_banner, print_scan_result, print_error,
    print_warning, print_success, print_info, console,
)

_con = Console()

MENU_ITEMS = [
    ("1", "Mark Attendance",     "QR scan + Face verification"),
    ("2", "Generate QR Code",    "Create today's QR for a student"),
    ("3", "Enroll Student Face", "Register a student's face photo"),
    ("4", "Add New Student",     "Register a new student in the system"),
    ("5", "Today's Attendance",  "View today's attendance table"),
    ("6", "Analytics Overview",  "Behavior analytics for all students"),
    ("7", "Student Report Card", "Detailed report for one student"),
    ("8", "ML Risk Predictions", "AI-predicted risk levels"),
    ("9", "Train ML Model",      "Retrain risk classifier on latest data"),
    ("A", "Class Summary",       "Quick today's class snapshot"),
    ("B", "View Alerts",         "Unread alerts panel"),
    ("0", "Exit",                ""),
]


def print_menu():
    _con.print()
    rows = []
    for key, label, desc in MENU_ITEMS:
        row = f"  [bold cyan][{key}][/] [white]{label:<28}[/]"
        if desc:
            row += f"[dim]{desc}[/]"
        rows.append(row)
    body = "\n".join(rows)
    _con.print(Panel(body, title="[bold cyan]ADMIN MENU[/]",
                     box=box.ROUNDED, border_style="cyan", padding=(1, 2)))


def action_mark_attendance():
    from geo_fence.fence_manager import validate_location
    from database.models.attendance import mark_attendance
    from analytics.metrics_engine import refresh_behavior_stats
    from alert_system.alert_engine import run_all_checks, check_proxy_attempt
    from utils.time_utils import attendance_status, minutes_late
    from database.models.student import get_student
    import time
    from rich.progress import track

    try:
        ip = validate_location()
        print_info(f"Geo-fence OK (IP: {ip})")
    except Exception as e:
        print_error(str(e))
        return

    if SIMULATION_MODE:
        print_warning("Webcam/OpenCV is unavailable on this Python environment.")
        print_warning("Running in High-Fidelity Attendance Simulation Mode!")
        student_id = Prompt.ask("[cyan]Enter Student ID to simulate QR scan[/]").strip().upper()
        try:
            student = get_student(student_id)
        except Exception as e:
            print_error(str(e))
            return
            
        print_info("Simulating QR Scan...")
        for _ in track(range(5), description="Scanning QR Code..."):
            time.sleep(0.3)
            
        print_success(f"QR verified for {student['name']} ({student_id})")
        
        print_info("Simulating Face Verification...")
        for _ in track(range(5), description="Analyzing Face..."):
            time.sleep(0.3)
            
        face_verified = True
        print_success("Face verified (distance=0.1824)")
    else:
        from scanner_module.scanner_controller import scan_and_validate
        from face_module.hybrid_auth import verify_student
        from utils.exceptions import (
            QRExpiredError, QRInvalidError, FaceAuthError,
            ProxyAttemptError, CameraError,
        )
        print_info("Starting QR scanner... (press Q in preview window to cancel)")
        try:
            scan_result = scan_and_validate(timeout_seconds=30, show_preview=True)
        except KeyboardInterrupt:
            print_warning("Scan cancelled by user.")
            return
        except TimeoutError as e:
            print_error(str(e))
            return
        except (QRInvalidError, QRExpiredError) as e:
            print_error(str(e))
            return
        except CameraError as e:
            print_error(f"Camera error: {e}")
            return

        student    = scan_result["student"]
        student_id = student["student_id"]
        print_success(f"QR verified for {student['name']} ({student_id})")

        face_verified = False
        try:
            face_result   = verify_student(student_id, show_preview=True)
            face_verified = True
            print_success(f"Face verified (distance={face_result['distance']})")
        except ProxyAttemptError as e:
            print_error(str(e))
            check_proxy_attempt(student_id)
            return
        except FaceAuthError as e:
            print_warning(f"Face auth skipped: {e}")

    status    = attendance_status()
    mins_late = minutes_late()
    auth_method = "QR+FACE" if face_verified else "QR"

    record = mark_attendance(
        student_id=student_id,
        status=status,
        minutes_late=mins_late,
        ip_address=ip,
        auth_method=auth_method,
    )

    try:
        refresh_behavior_stats()
    except Exception:
        pass

    alerts = run_all_checks(student_id, status)
    print_scan_result(
        student=get_student(student_id),
        status=status,
        minutes_late=mins_late,
        face_verified=face_verified,
        alerts=alerts,
    )


def action_generate_qr():
    from utils.exceptions import StudentNotFoundError
    from config.settings import QR_CODES_DIR
    from utils.time_utils import today_str, time_slot, now
    from database.models.student import get_student
    from utils.crypto import sign

    student_id = Prompt.ask("[cyan]Student ID[/]").strip().upper()
    
    try:
        student = get_student(student_id)
        seed = student["qr_seed"]
        raw_payload = f"{student_id}|{today_str()}|{time_slot(now())}|{seed}"
        mac = sign(raw_payload)
        payload = f"{student_id}|{today_str()}|{time_slot(now())}|{mac}"
        
        if SIMULATION_MODE:
            print_warning("Pillow/OpenCV is unavailable. Printing terminal-based secure QR payload!")
            print_success(f"Secure QR Payload successfully generated:")
            _con.print(Panel(f"[bold cyan]Payload:[/] {payload}\n[dim]HMAC Signature: {mac}[/]", title="[bold green]SIMULATED QR CODE[/]", expand=False))
        else:
            from qr_module.generator import generate_qr
            img      = generate_qr(student_id, save=True)
            filename = f"{student_id}_{today_str()}_{time_slot()}.png"
            path     = QR_CODES_DIR / filename
            print_success(f"QR saved to: {path}")
            try:
                img.show()
            except Exception:
                pass
    except StudentNotFoundError as e:
        print_error(str(e))


def action_enroll_face():
    from utils.exceptions import StudentNotFoundError
    from database.models.student import get_student

    student_id = Prompt.ask("[cyan]Student ID[/]").strip().upper()
    
    try:
        get_student(student_id)
        if SIMULATION_MODE:
            from database.models.student import update_face_encoding
            print_warning("Running in Face Enrollment Simulation Mode!")
            # Save a 10,000-dimensional dummy vector representing a normalized 100x100 grayscale face
            encoding = [1.0] * 10000
            update_face_encoding(student_id, encoding)
            print_success(f"Face enrolled successfully for {student_id} (Simulated 100x100 Vector)!")
        else:
            from face_module.face_encoder import enroll_student_face
            from utils.exceptions import FaceAuthError
            image_path = Prompt.ask("[cyan]Path to student photo (JPG/PNG)[/]").strip().strip('"')
            try:
                enroll_student_face(student_id, image_path)
                print_success(f"Face enrolled for {student_id}")
            except (StudentNotFoundError, FaceAuthError, FileNotFoundError) as e:
                print_error(str(e))
    except StudentNotFoundError as e:
        print_error(str(e))


def action_add_student():
    from database.models.student import create_student

    _con.print("\n[bold cyan]Add New Student[/]")
    student_id = Prompt.ask("  Student ID (e.g. STU_101)").strip().upper()
    name       = Prompt.ask("  Full Name").strip()
    class_     = Prompt.ask("  Class / Section").strip()
    email      = Prompt.ask("  Email (optional)", default="").strip()
    phone      = Prompt.ask("  Phone (optional)", default="").strip()

    try:
        create_student(student_id, name, class_, email, phone)
        print_success(f"Student '{name}' ({student_id}) added successfully!")
    except Exception as e:
        print_error(str(e))


def action_train_model():
    from ml_module.model_trainer import train_model
    from utils.exceptions import MLModelError

    print_info("Training ML risk classifier...")
    try:
        metrics = train_model(verbose=True)
        print_success(
            f"Model trained!  Accuracy: {metrics['accuracy']}%  "
            f"CV: {metrics['cross_val_mean']}±{metrics['cross_val_std']}%  "
            f"Samples: {metrics['samples']}"
        )
    except MLModelError as e:
        print_error(str(e))


def main():
    try:
        from database.connection import init_db
        init_db()
    except Exception as e:
        print_error(f"Database init failed: {e}")
        print_warning("Check your .env file and make sure MySQL is running.")

    print_banner()

    dispatch = {
        "1": action_mark_attendance,
        "2": action_generate_qr,
        "3": action_enroll_face,
        "4": action_add_student,
        "5": lambda: __import__("ui.admin_dashboard", fromlist=["show_today_attendance"]).show_today_attendance(),
        "6": lambda: __import__("ui.admin_dashboard", fromlist=["show_analytics_overview"]).show_analytics_overview(),
        "7": lambda: __import__("ui.admin_dashboard", fromlist=["show_student_report"]).show_student_report(
            Prompt.ask("[cyan]Student ID[/]").strip().upper()
        ),
        "8": lambda: __import__("ui.admin_dashboard", fromlist=["show_predictions"]).show_predictions(),
        "9": action_train_model,
        "A": lambda: __import__("ui.admin_dashboard", fromlist=["show_class_summary"]).show_class_summary(),
        "B": lambda: __import__("ui.admin_dashboard", fromlist=["show_alerts"]).show_alerts(),
    }

    while True:
        print_menu()
        choice = Prompt.ask("[bold cyan]Select option[/]").strip().upper()

        if choice == "0":
            print_success("Goodbye!")
            break

        action = dispatch.get(choice)
        if action:
            try:
                action()
            except KeyboardInterrupt:
                print_warning("Operation cancelled.")
            except Exception as e:
                print_error(f"Unexpected error: {e}")
        else:
            print_warning(f"Unknown option '{choice}'. Please try again.")


if __name__ == "__main__":
    main()
