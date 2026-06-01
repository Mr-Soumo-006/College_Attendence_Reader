"""
Smart Campus Web Portal — Entry Point
=======================================
Run this script to start the web portal:

    python run_web.py

Then open http://localhost:5000 in your browser.
"""

import sys
import os

# Ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=False)


def main():
    """Initialize database and start the Flask web server."""
    # Initialize the database (create tables if they don't exist)
    try:
        from database.connection import init_db
        init_db()
        print("[OK] Database initialized successfully.")
    except Exception as e:
        print(f"[WARNING] Database init issue: {e}")
        print("[INFO] Make sure MySQL is running and .env is configured correctly.")

    # Create and run the Flask app
    from ui.web.web_app import create_app
    app = create_app()

    print()
    print("=" * 60)
    print("  SMART CAMPUS WEB PORTAL")
    print("=" * 60)
    print()
    print("  Student Portal:  http://localhost:5000/login")
    print("  Teacher Portal:  http://localhost:5000/login")
    print()
    print("  Teacher Password: (set in .env TEACHER_PASSWORD)")
    print()
    print("=" * 60)
    print()

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True,
        use_reloader=True,
    )


if __name__ == "__main__":
    main()
