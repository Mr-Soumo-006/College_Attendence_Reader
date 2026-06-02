"""
WSGI Entry Point for Cloud Deployment (Render/AlwaysData).
"""

import sys
import os

# Ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.connection import init_db
from ui.web.web_app import create_app

# Automatically run database setup and migrations at startup
try:
    init_db()
    print("[OK] Cloud database initialization/migration completed successfully.")
except Exception as e:
    print(f"[WARNING] Database initialization skipped or encountered an error: {e}")

app = create_app()
