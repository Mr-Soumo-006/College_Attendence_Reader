"""
Smart Campus Web Portal — Flask Application
=============================================
Serves the student and teacher web dashboards.
Connects to the same MySQL backend as the CLI admin tool.
"""

import sys
import os
from io import BytesIO
from functools import wraps

# Ensure project root is on sys.path
# web_app.py is at ui/web/web_app.py — go up 3 levels to reach project root
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, send_file, jsonify,
)

from config.settings import (
    QR_SECRET_KEY, QR_VALIDITY_MINUTES,
    CLASS_START_TIME, LATE_THRESHOLD_MIN, TIMEZONE,
    COLLEGE_LAT, COLLEGE_LNG, GEOFENCE_RADIUS_METERS,
)
from database.connection import DBConnection, init_db
from database.models.student import (
    get_student, get_all_students, create_student, delete_student,
)
from database.models.attendance import (
    get_history, get_all_today, get_today_record, mark_attendance,
)
from analytics.metrics_engine import (
    compute_all_stats, get_student_summary, refresh_behavior_stats,
)
from analytics.report_builder import class_summary_report, student_report_card
from analytics.pattern_detector import analyze_dow_pattern, trend_analysis
from ml_module.predictor import predict_all_students
from database.models.alert import get_unread_alerts
from database.models.attendance_session import get_active_session, create_session, end_active_session
from database.models.student_rating import submit_rating, get_student_ratings, get_all_ratings
from utils.exceptions import StudentNotFoundError, DatabaseError
from utils.time_utils import now, today_str, time_slot
from utils.crypto import sign


# ── Flask App Factory ─────────────────────────────────────────

def create_app():
    """Create and configure the Flask application."""
    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(__file__), "templates"),
    )

    # Load secret key from .env or use fallback
    app.secret_key = os.getenv(
        "FLASK_SECRET_KEY",
        "smart_campus_flask_secret_change_me_in_production",
    )
    app.config["TEACHER_PASSWORD"] = os.getenv("TEACHER_PASSWORD", "admin123")
    app.config["COLLEGE_LAT"] = COLLEGE_LAT
    app.config["COLLEGE_LNG"] = COLLEGE_LNG
    app.config["GEOFENCE_RADIUS_METERS"] = GEOFENCE_RADIUS_METERS

    # ── Auth Decorators ───────────────────────────────────────

    def login_required(role):
        """Decorator: require logged-in user with given role."""
        def decorator(f):
            @wraps(f)
            def wrapper(*args, **kwargs):
                if "user_role" not in session or session["user_role"] != role:
                    flash("Please log in to continue.", "warning")
                    # Capture the attempted path to redirect back after login
                    next_url = request.full_path if request.query_string else request.path
                    return redirect(url_for("login", next=next_url))
                return f(*args, **kwargs)
            return wrapper
        return decorator

    # ── Routes: General ───────────────────────────────────────

    @app.route("/")
    def index():
        """Redirect to login page."""
        if "user_role" in session:
            if session["user_role"] == "student":
                return redirect(url_for("student_dashboard"))
            elif session["user_role"] == "teacher":
                return redirect(url_for("teacher_dashboard"))
        return redirect(url_for("login"))

    @app.route("/login", methods=["GET", "POST"])
    def login():
        """Dual-tab login for students and teachers."""
        if request.method == "POST":
            role = request.form.get("role", "student")

            if role == "student":
                student_id = request.form.get("student_id", "").strip().upper()
                if not student_id:
                    flash("Please enter your Student ID.", "error")
                    return render_template("login.html", active_tab="student")
                try:
                    student = get_student(student_id)
                    session["user_role"] = "student"
                    session["user_id"] = student_id
                    session["user_name"] = student["name"]
                    flash(f"Welcome, {student['name']}!", "success")
                    next_url = request.args.get("next")
                    if next_url and next_url.startswith("/"):
                        return redirect(next_url)
                    return redirect(url_for("student_dashboard"))
                except StudentNotFoundError:
                    flash("Student ID not found. Please check and try again.", "error")
                    return render_template("login.html", active_tab="student")

            elif role == "teacher":
                teacher_id = request.form.get("teacher_id", "").strip().upper()
                password = request.form.get("password", "")
                if not teacher_id or not password:
                    flash("Please fill in all fields.", "error")
                    return render_template("login.html", active_tab="teacher")
                
                from database.models.teacher import verify_teacher_login
                teacher = verify_teacher_login(teacher_id, password)
                if not teacher:
                    flash("Invalid teacher ID or password.", "error")
                    return render_template("login.html", active_tab="teacher")
                
                session["user_role"] = "teacher"
                session["user_id"] = teacher["teacher_id"]
                session["user_name"] = teacher["name"]
                flash(f"Welcome, {teacher['name']}!", "success")
                next_url = request.args.get("next")
                if next_url and next_url.startswith("/"):
                    return redirect(next_url)
                return redirect(url_for("teacher_dashboard"))

        return render_template("login.html", active_tab="student")

    @app.route("/logout")
    def logout():
        """Clear session and redirect to login."""
        session.clear()
        flash("You have been logged out.", "info")
        return redirect(url_for("login"))

    # ── Routes: Student Dashboard ─────────────────────────────

    @app.route("/student")
    @login_required("student")
    def student_dashboard():
        """Main student dashboard with KPIs, QR, history, and patterns."""
        student_id = session["user_id"]
        try:
            student = get_student(student_id)
        except StudentNotFoundError:
            session.clear()
            flash("Student not found. Please log in again.", "error")
            return redirect(url_for("login"))

        # Gather all data for the dashboard
        stats = get_student_summary(student_id) or {}
        history = get_history(student_id, days=30)
        today_record = get_today_record(student_id)

        # Compute stats from all_stats if behavior_stats is empty
        if not stats:
            all_stats = compute_all_stats()
            for s in all_stats:
                if s["student_id"] == student_id:
                    stats = s
                    break

        # Day-of-week pattern
        try:
            dow_pattern = analyze_dow_pattern(student_id)
        except Exception:
            dow_pattern = {}

        # Trend analysis
        try:
            trend = trend_analysis(student_id)
        except Exception:
            trend = "STABLE"

        # Subject ratings and teacher feedback comments
        try:
            ratings = get_student_ratings(student_id)
        except Exception:
            ratings = []

        return render_template(
            "student_dashboard.html",
            student=student,
            stats=stats,
            history=history,
            today_record=today_record,
            dow_pattern=dow_pattern,
            trend=trend,
            ratings=ratings,
        )

    @app.route("/mark-attendance", methods=["GET"])
    @login_required("student")
    def mark_attendance_page():
        """Render the mobile-friendly attendance marking page."""
        student_id = session["user_id"]
        try:
            student = get_student(student_id)
        except StudentNotFoundError:
            session.clear()
            flash("Student not found. Please log in again.", "error")
            return redirect(url_for("login"))

        today_record = get_today_record(student_id)
        active_session = get_active_session()
        return render_template(
            "mark_attendance.html",
            student=student,
            today_record=today_record,
            active_session=active_session,
            college_lat=app.config.get("COLLEGE_LAT", COLLEGE_LAT),
            college_lng=app.config.get("COLLEGE_LNG", COLLEGE_LNG),
            geofence_radius=app.config.get("GEOFENCE_RADIUS_METERS", GEOFENCE_RADIUS_METERS)
        )

    @app.route("/mark-attendance", methods=["POST"])
    @login_required("student")
    def mark_attendance_post():
        """Receive lat/lng from student's browser and mark attendance."""
        student_id = session["user_id"]
        
        # Check active session lock
        active_session = get_active_session()
        if not active_session:
            return jsonify({"status": "error", "message": "Attendance check-in blocked: No active class session is currently running."}), 403
        
        # Parse JSON payload
        data = request.get_json() or {}
        lat = data.get("lat")
        lng = data.get("lng")

        if lat is None or lng is None:
            return jsonify({"status": "error", "message": "Location data is missing. Please enable GPS."}), 400

        try:
            lat = float(lat)
            lng = float(lng)
        except ValueError:
            return jsonify({"status": "error", "message": "Invalid GPS coordinates format."}), 400

        # Validate GPS Geofence
        try:
            from geo_fence.fence_manager import validate_gps_location
            distance = validate_gps_location(lat, lng)
        except GeoFenceViolation as e:
            return jsonify({"status": "error", "message": str(e)}), 403
        except Exception as e:
            return jsonify({"status": "error", "message": f"Geo-fence validation failed: {str(e)}"}), 500

        # Check if already marked today
        try:
            today_record = get_today_record(student_id)
            if today_record:
                return jsonify({
                    "status": "success",
                    "message": "Attendance already marked today.",
                    "already_marked": True,
                    "record": {
                        "date": today_record["date"],
                        "time_in": str(today_record["time_in"]),
                        "status": today_record["status"],
                        "minutes_late": today_record["minutes_late"]
                    }
                })

            # Determine attendance status and minutes late
            from utils.time_utils import attendance_status as get_status, minutes_late as get_mins_late
            status = get_status()
            mins_late = get_mins_late()

            # Client IP
            client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
            if client_ip and ',' in client_ip:
                client_ip = client_ip.split(',')[0].strip()
            elif not client_ip:
                client_ip = request.remote_addr or "127.0.0.1"

            # Mark in Database
            record = mark_attendance(
                student_id=student_id,
                status=status,
                minutes_late=mins_late,
                ip_address=client_ip,
                auth_method="GPS"
            )

            # Trigger analytics refresh
            try:
                refresh_behavior_stats()
            except Exception:
                pass

            # Trigger alert engine checks
            try:
                from alert_system.alert_engine import run_all_checks
                run_all_checks(student_id, status)
            except Exception:
                pass

            return jsonify({
                "status": "success",
                "message": f"Attendance marked successfully as {status}!",
                "record": {
                    "date": record["date"],
                    "time_in": str(record["time_in"]),
                    "status": record["status"],
                    "minutes_late": record["minutes_late"]
                }
            })

        except Exception as e:
            return jsonify({"status": "error", "message": f"Database error: {str(e)}"}), 500

    # ── Routes: Teacher Dashboard ─────────────────────────────

    @app.route("/teacher/generate-poster")
    @login_required("teacher")
    def generate_poster():
        """Teacher-only page to view and print the campus static QR poster."""
        # Build the static URL that students will scan:
        # We dynamically use the current request's host to support HTTPS tunnels (like ngrok) seamlessly!
        poster_url = f"{request.host_url.rstrip('/')}/mark-attendance"
        
        # Generate the QR code for this URL
        try:
            import qrcode
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=10,
                border=4,
            )
            qr.add_data(poster_url)
            qr.make(fit=True)

            img = qr.make_image(
                fill_color="#7c3aed",
                back_color="#0f0e17",
            ).convert("RGBA")

            # Save QR to a bytes stream
            buf = BytesIO()
            img.save(buf, format="PNG")
            buf.seek(0)
            
            # Encode as base64 so we can embed it directly in the HTML template
            import base64
            qr_base64 = base64.b64encode(buf.getvalue()).decode()
            qr_img_src = f"data:image/png;base64,{qr_base64}"
        except Exception:
            # Fallback placeholder if qrcode library fails
            qr_img_src = None

        return render_template(
            "poster_qr.html",
            poster_url=poster_url,
            qr_img_src=qr_img_src,
            teacher_name=session.get("user_name", "Teacher")
        )

    @app.route("/teacher")
    @login_required("teacher")
    def teacher_dashboard():
        """Main teacher dashboard with overview, analytics, predictions, alerts."""
        # Class summary for today
        try:
            summary = class_summary_report()
        except Exception:
            summary = {
                "date": today_str(),
                "total_students": 0,
                "present": 0,
                "late": 0,
                "absent": 0,
                "attendance_rate": 0,
                "high_risk_count": 0,
            }

        # All student analytics
        try:
            all_stats = compute_all_stats()
        except Exception:
            all_stats = []

        # ML predictions
        try:
            predictions = predict_all_students()
        except Exception:
            predictions = []

        # Unread alerts
        try:
            alerts = get_unread_alerts()
        except Exception:
            alerts = []

        # Today's attendance records
        try:
            today_records = get_all_today()
        except Exception:
            today_records = []

        # All students for add form validation
        try:
            students = get_all_students()
        except Exception:
            students = []

        # All teachers for registry list
        try:
            from database.models.teacher import get_all_teachers
            teachers = get_all_teachers()
        except Exception:
            teachers = []

        # Active attendance session
        try:
            active_session = get_active_session()
        except Exception:
            active_session = None

        # All academic ratings
        try:
            all_ratings = get_all_ratings()
        except Exception:
            all_ratings = []

        return render_template(
            "teacher_dashboard.html",
            summary=summary,
            all_stats=all_stats,
            predictions=predictions,
            alerts=alerts,
            today_records=today_records,
            students=students,
            teachers=teachers,
            teacher_name=session.get("user_name", "Teacher"),
            current_teacher_id=session.get("user_id", ""),
            active_session=active_session,
            all_ratings=all_ratings,
        )

    @app.route("/teacher/add-student", methods=["POST"])
    @login_required("teacher")
    def add_student():
        """Add a new student from the teacher dashboard."""
        student_id = request.form.get("student_id", "").strip().upper()
        name = request.form.get("name", "").strip()
        department = request.form.get("department", "").strip().upper()
        year = request.form.get("year", "").strip()
        semester = request.form.get("semester", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()

        if not student_id or not name or not department or not year or not semester:
            flash("Student ID, Name, Department, Year, and Semester are required.", "error")
            return redirect(url_for("teacher_dashboard"))

        try:
            year = int(year)
            semester = int(semester)
            if not (1 <= year <= 4):
                raise ValueError("Invalid year selected (must be 1-4).")
            if not (1 <= semester <= 8):
                raise ValueError("Invalid semester selected (must be 1-8).")
            
            # Check year-semester mapping validity
            # Year 1: Sem 1-2, Year 2: Sem 3-4, Year 3: Sem 5-6, Year 4: Sem 7-8
            expected_year = (semester + 1) // 2
            if expected_year != year:
                raise ValueError(f"Semester {semester} does not belong to Year {year} (expected Year {expected_year}).")

            create_student(student_id, name, department, year, semester, email, phone)
            flash(f"Student '{name}' ({student_id}) added successfully!", "success")
        except Exception as e:
            flash(f"Error adding student: {e}", "error")

        return redirect(url_for("teacher_dashboard"))

    @app.route("/teacher/add-teacher", methods=["POST"])
    @login_required("teacher")
    def add_teacher():
        """Register a new teacher from the teacher dashboard."""
        teacher_id = request.form.get("teacher_id", "").strip().upper()
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        department = request.form.get("department", "").strip().upper()
        password = request.form.get("password", "")

        if not teacher_id or not name or not email or not department or not password:
            flash("All fields are required to register a teacher.", "error")
            return redirect(url_for("teacher_dashboard"))

        try:
            from database.models.teacher import create_teacher
            create_teacher(teacher_id, name, email, department, password)
            flash(f"Teacher '{name}' ({teacher_id}) registered successfully!", "success")
        except Exception as e:
            flash(f"Error registering teacher: {e}", "error")

        return redirect(url_for("teacher_dashboard"))

    @app.route("/teacher/delete-student/<student_id>", methods=["POST"])
    @login_required("teacher")
    def delete_student_route(student_id):
        """Physically delete a student from the system."""
        try:
            student = get_student(student_id)
            delete_student(student_id)
            flash(f"Student '{student['name']}' ({student_id}) has been successfully deleted.", "success")
        except Exception as e:
            flash(f"Error deleting student: {e}", "error")
        return redirect(url_for("teacher_dashboard"))

    @app.route("/teacher/delete-teacher/<teacher_id>", methods=["POST"])
    @login_required("teacher")
    def delete_teacher_route(teacher_id):
        """Physically delete a teacher from the system."""
        current_teacher_id = session.get("user_id", "")
        if teacher_id.upper() == current_teacher_id.upper():
            flash("Error: You cannot delete your own account while logged in.", "error")
            return redirect(url_for("teacher_dashboard"))

        try:
            from database.models.teacher import get_teacher, delete_teacher
            teacher = get_teacher(teacher_id)
            if not teacher:
                flash("Teacher not found.", "error")
                return redirect(url_for("teacher_dashboard"))
                
            delete_teacher(teacher_id)
            flash(f"Teacher '{teacher['name']}' ({teacher_id}) has been successfully deleted.", "success")
        except Exception as e:
            flash(f"Error deleting teacher: {e}", "error")
        return redirect(url_for("teacher_dashboard"))

    @app.route("/teacher/refresh-stats", methods=["POST"])
    @login_required("teacher")
    def refresh_stats():
        """Manually trigger a refresh of behavior statistics."""
        try:
            refresh_behavior_stats()
            flash("Behavior statistics refreshed successfully!", "success")
        except Exception as e:
            flash(f"Error refreshing stats: {e}", "error")
        return redirect(url_for("teacher_dashboard"))

    @app.route("/teacher/start-session", methods=["POST"])
    @login_required("teacher")
    def start_session():
        """Create and start a new active timed attendance session."""
        session_name = request.form.get("session_name", "").strip()
        duration = request.form.get("duration", "").strip()
        teacher_id = session.get("user_id")

        if not session_name or not duration:
            flash("Session subject/name and duration are required.", "error")
            return redirect(url_for("teacher_dashboard"))

        try:
            duration = int(duration)
            if duration <= 0:
                raise ValueError("Duration must be a positive integer.")
            
            create_session(session_name, teacher_id, duration)
            flash(f"Attendance session '{session_name}' started successfully for {duration} minutes!", "success")
        except Exception as e:
            flash(f"Error starting session: {e}", "error")

        return redirect(url_for("teacher_dashboard"))

    @app.route("/teacher/end-session", methods=["POST"])
    @login_required("teacher")
    def end_session():
        """Manually close the currently active attendance session."""
        try:
            end_active_session()
            flash("Active attendance session closed successfully.", "success")
        except Exception as e:
            flash(f"Error closing session: {e}", "error")
        return redirect(url_for("teacher_dashboard"))

    @app.route("/teacher/submit-rating", methods=["POST"])
    @login_required("teacher")
    def submit_rating_route():
        """Submit or update a student's subject-wise rating and feedback."""
        student_id = request.form.get("student_id", "").strip().upper()
        subject = request.form.get("subject", "").strip()
        rating = request.form.get("rating", "").strip()
        comment = request.form.get("comment", "").strip()
        teacher_id = session.get("user_id")

        if not student_id or not subject or not rating or not comment:
            flash("Student ID, Subject, Rating, and Comments are required.", "error")
            return redirect(url_for("teacher_dashboard"))

        try:
            rating = int(rating)
            if not (1 <= rating <= 5):
                raise ValueError("Rating must be between 1 and 5.")
            
            # Verify student exists first
            get_student(student_id)
            
            submit_rating(student_id, teacher_id, subject, rating, comment)
            flash(f"Subject rating for student '{student_id}' in '{subject}' submitted successfully!", "success")
        except Exception as e:
            flash(f"Error submitting rating: {e}", "error")

        return redirect(url_for("teacher_dashboard"))

    # ── Helpers ────────────────────────────────────────────────

    def _generate_fallback_qr_svg(payload):
        """Generate a minimal SVG placeholder when qrcode library is unavailable."""
        svg = f"""<?xml version="1.0" encoding="UTF-8"?>
        <svg xmlns="http://www.w3.org/2000/svg" width="300" height="300" viewBox="0 0 300 300">
            <rect width="300" height="300" fill="#0f0e17" rx="16"/>
            <rect x="40" y="40" width="220" height="220" fill="none" stroke="#7c3aed"
                  stroke-width="3" rx="12" stroke-dasharray="8,4"/>
            <text x="150" y="140" text-anchor="middle" fill="#a855f7"
                  font-family="monospace" font-size="14" font-weight="bold">QR CODE</text>
            <text x="150" y="170" text-anchor="middle" fill="#6b7280"
                  font-family="monospace" font-size="10">{payload[:30]}...</text>
        </svg>"""
        return svg, 200, {"Content-Type": "image/svg+xml"}

    # ── Jinja2 Template Filters ───────────────────────────────

    @app.template_filter("risk_color")
    def risk_color_filter(risk_level):
        """Return CSS class for risk level badge."""
        colors = {
            "LOW": "badge-green",
            "MEDIUM": "badge-amber",
            "HIGH": "badge-red",
        }
        return colors.get(risk_level, "badge-gray")

    @app.template_filter("status_color")
    def status_color_filter(status):
        """Return CSS class for attendance status badge."""
        colors = {
            "ON TIME": "badge-green",
            "LATE": "badge-amber",
            "ABSENT": "badge-red",
        }
        return colors.get(status, "badge-gray")

    @app.template_filter("severity_color")
    def severity_color_filter(severity):
        """Return CSS class for alert severity badge."""
        colors = {
            "INFO": "badge-cyan",
            "WARNING": "badge-amber",
            "CRITICAL": "badge-red",
        }
        return colors.get(severity, "badge-gray")

    @app.template_filter("format_pct")
    def format_pct_filter(value):
        """Format a float as a percentage string."""
        try:
            return f"{float(value):.1f}%"
        except (TypeError, ValueError):
            return "0.0%"

    # ── Context Processors ────────────────────────────────────

    @app.context_processor
    def inject_globals():
        """Inject global template variables."""
        return {
            "current_time": now(),
            "today": today_str(),
            "app_name": "Smart Campus",
        }

    return app
