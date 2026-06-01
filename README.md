# 🎓 Smart Campus Attendance System

A CLI-based student attendance management system featuring **QR code scanning**, **facial recognition**, **geo-fencing**, **behavior analytics**, and **ML-based risk prediction**.

---

## 📋 Features

| Feature              | Description                                                       |
|----------------------|-------------------------------------------------------------------|
| **QR Attendance**    | Time-bound, HMAC-signed QR codes that expire every hour           |
| **Face Verification**| Dual-factor: QR + live face recognition via webcam (pure OpenCV)  |
| **Geo-Fencing**      | IP-based campus network validation (blocks off-campus attempts)   |
| **Analytics**        | Per-student KPIs: absence %, late %, streaks, day-of-week trends  |
| **ML Risk Prediction**| RandomForest classifier predicts at-risk students               |
| **Alert System**     | Auto-fires alerts for late streaks, absences, proxy attempts      |
| **Rich Console UI**  | Beautiful terminal dashboard with tables, panels, and colors      |

---

## 🛠️ Prerequisites

Before installing, make sure you have:

### 1. Python 3.10+ (Including Python 3.14.5+)
Download from [python.org](https://www.python.org/downloads/). During installation on Windows, **check "Add Python to PATH"**.

### 2. MySQL Server 8.0+
- **Windows:** Download [MySQL Installer](https://dev.mysql.com/downloads/installer/) and install MySQL Server. Remember the root password you set.
- **macOS:** `brew install mysql && brew services start mysql`
- **Linux:** `sudo apt install mysql-server && sudo systemctl start mysql`

### 3. Webcam
Required for QR scanning and face verification features.

---

## 🚀 Installation

### Step 1: Clone / Navigate to the project

```bash
cd smart_campus/smart_campus
```

### Step 2: Create a virtual environment (recommended)

```bash
# Create virtual environment
python -m venv venv

# Activate it:
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1

# Windows (CMD):
.\venv\Scripts\activate.bat

# macOS / Linux:
source venv/bin/activate
```

### Step 3: Install dependencies

```bash
pip install -r requirements.txt
```

> **🎉 No Compiler Required!** This project uses custom, optimized facial recognition algorithms built entirely on standard `opencv-python`. You **do not** need to install Visual Studio C++ Build Tools, CMake, or compile heavy libraries.

> **⚠️ `pyzbar` on Windows:** The `pyzbar` library requires the ZBar shared library.
> Install the [Visual C++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe) if you get DLL errors.

### Step 4: Configure environment variables

Edit the `.env` file in the project root:

```ini
# REQUIRED — Set your MySQL root password:
DB_PASSWORD=your_actual_mysql_password

# RECOMMENDED — Change the QR secret key:
QR_SECRET_KEY=some_random_32_character_string_here

# OPTIONAL — Email settings (if you want alert emails):
EMAIL_ENABLED=true
EMAIL_USER=your_email@gmail.com
EMAIL_PASSWORD=your_app_password
```

### Step 5: Verify MySQL is running

```bash
# Windows (PowerShell):
Get-Service -Name "MySQL*"

# macOS:
brew services list | grep mysql

# Linux:
sudo systemctl status mysql
```

---

## ▶️ Running the Application

```bash
python main.py
```

This will:
1. **Auto-create the database** and all tables (from `database/schema.sql`)
2. **Auto-create data directories** (`data/`, `data/student_faces/`, `data/qr_codes/`, `logs/`, `ml_module/saved_models/`)
3. Display the **Admin Menu**

### Admin Menu Options

```
┌──────────── ADMIN MENU ────────────┐
│  [1] Mark Attendance       QR scan + Face verification       │
│  [2] Generate QR Code      Create today's QR for a student   │
│  [3] Enroll Student Face   Register a student's face photo   │
│  [4] Add New Student       Register a new student            │
│  [5] Today's Attendance    View today's attendance table     │
│  [6] Analytics Overview    Behavior analytics for all        │
│  [7] Student Report Card   Detailed report for one student   │
│  [8] ML Risk Predictions   AI-predicted risk levels          │
│  [9] Train ML Model        Retrain risk classifier           │
│  [A] Class Summary         Quick today's class snapshot      │
│  [B] View Alerts           Unread alerts panel               │
│  [0] Exit                                                    │
└──────────────────────────────────────────────────────────────┘
```

---

## 📖 Quick Start Guide (First-time use)

1. **Start the app:** `python main.py`
2. **Add a student:** Select option `4`, enter student ID (e.g., `STU_101`), name, class, etc.
3. **Enroll their face:** Select option `3`, enter the student ID and path to a clear face photo
4. **Generate a QR code:** Select option `2`, enter the student ID → a QR image opens and is saved
5. **Mark attendance:** Select option `1` → show the QR to the webcam → face verification follows
6. **View attendance:** Select option `5` to see today's records
7. **Train ML model:** After enough attendance data (≥10 records), select option `9`
8. **View predictions:** Select option `8` to see AI risk predictions

---

## 📁 Project Structure

```
smart_campus/
├── main.py                    # CLI entry point & menu loop
├── .env                       # Environment configuration
├── requirements.txt           # Python dependencies
│
├── config/
│   └── settings.py            # Centralized config loader
│
├── database/
│   ├── connection.py          # MySQL connection pool & context manager
│   ├── schema.sql             # Database schema (5 tables)
│   └── models/
│       ├── student.py         # Student CRUD operations
│       ├── attendance.py      # Attendance CRUD operations
│       └── alert.py           # Alert CRUD operations
│
├── scanner_module/
│   ├── camera.py              # OpenCV webcam wrapper
│   ├── scanner_controller.py  # QR scan loop + decode
│   └── validator.py           # QR HMAC verification + expiry check
│
├── face_module/
│   ├── face_encoder.py        # Face enrollment (image → 100x100 matrix)
│   ├── face_matcher.py        # Face comparison (Pearson correlation distance)
│   └── hybrid_auth.py         # Live webcam face verification flow
│
├── qr_module/
│   └── generator.py           # HMAC-signed QR code generation
│
├── geo_fence/
│   └── fence_manager.py       # IP-based campus network validation
│
├── analytics/
│   ├── metrics_engine.py      # Per-student KPI computation + risk levels
│   ├── pattern_detector.py    # DOW patterns, trends, Z-score anomalies
│   └── report_builder.py      # Summary reports for dashboard
│
├── ml_module/
│   ├── feature_engineering.py # 8-feature matrix from attendance data
│   ├── model_trainer.py       # RandomForest training + persistence
│   └── predictor.py           # Real-time risk prediction
│
├── alert_system/
│   └── alert_engine.py        # Rule-based alert checks
│
├── ui/
│   ├── console_ui.py          # Banners, colored output helpers
│   └── admin_dashboard.py     # Rich console tables & panels
│
└── utils/
    ├── crypto.py              # HMAC-SHA256 signing for QR integrity
    ├── exceptions.py          # 9 custom exception classes
    └── time_utils.py          # Timezone-aware time utilities
```

---

## 🗄️ Database Schema

The system auto-creates these 5 tables:

| Table              | Purpose                                |
|--------------------|----------------------------------------|
| `students`         | Student records with face encodings    |
| `attendance`       | Daily attendance logs                  |
| `behavior_stats`   | Cached analytics KPIs per student      |
| `alerts`           | Triggered alert history                |
| `system_logs`      | System event logs                      |

---

## ⚙️ Configuration Reference (.env)

| Variable               | Default          | Description                              |
|------------------------|------------------|------------------------------------------|
| `DB_HOST`              | `localhost`      | MySQL server hostname                    |
| `DB_PORT`              | `3306`           | MySQL server port                        |
| `DB_NAME`              | `smart_campus`   | Database name                            |
| `DB_USER`              | `root`           | MySQL username                           |
| `DB_PASSWORD`          | *(empty)*        | MySQL password — **must set this**       |
| `QR_SECRET_KEY`        | *(placeholder)*  | HMAC key for QR signing — **change this**|
| `QR_VALIDITY_MINUTES`  | `60`             | QR code expiry window (minutes)          |
| `CAMERA_INDEX`         | `0`              | Webcam device index                      |
| `FACE_TOLERANCE`       | `0.5`            | Face match threshold (lower = stricter)  |
| `ALLOWED_IP_PREFIXES`  | `192.168.1.,...` | Campus network IP prefixes               |
| `CLASS_START_TIME`     | `09:00`          | Class start time (HH:MM)                |
| `LATE_THRESHOLD_MINUTES`| `15`            | Grace period before marking late         |
| `TIMEZONE`             | `Asia/Kolkata`   | System timezone                          |

---

## 🐛 Troubleshooting

| Problem                                      | Solution                                                                 |
|----------------------------------------------|--------------------------------------------------------------------------|
| `ModuleNotFoundError: No module named 'pyzbar'` | Run `pip install pyzbar==0.1.9`                                      |
| `ImportError: Unable to find zbar shared library` | Install [VC++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe) |
| `Database init failed`                       | Check MySQL is running and `.env` credentials are correct                |
| `Cannot open camera at index 0`              | Close other apps using the webcam, or set `CAMERA_INDEX=1` in `.env`     |
| `No timezone data` / `ZoneInfoNotFoundError` | Run `pip install tzdata`                                                 |

---

## 📄 License

This project is for educational purposes.
