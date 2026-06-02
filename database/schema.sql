-- ============================================================
-- Smart Campus Attendance System — Database Schema
-- ============================================================

CREATE DATABASE IF NOT EXISTS smart_campus
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE smart_campus;

-- ── Teachers ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS teachers (
    id          INT          AUTO_INCREMENT PRIMARY KEY,
    teacher_id  VARCHAR(20)  NOT NULL UNIQUE,
    name        VARCHAR(100) NOT NULL,
    email       VARCHAR(120) NOT NULL UNIQUE,
    department  VARCHAR(50)  NOT NULL,
    password    VARCHAR(255) NOT NULL,
    created_at  DATETIME     DEFAULT CURRENT_TIMESTAMP
);

-- ── Students ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS students (
    id             INT          AUTO_INCREMENT PRIMARY KEY,
    student_id     VARCHAR(20)  NOT NULL UNIQUE,
    name           VARCHAR(100) NOT NULL,
    class          VARCHAR(50)  NOT NULL,
    email          VARCHAR(120),
    phone          VARCHAR(20),
    qr_seed        VARCHAR(64)  NOT NULL,
    face_encoding  LONGTEXT,
    risk_level     ENUM('LOW','MEDIUM','HIGH') DEFAULT 'LOW',
    enrolled_at    DATETIME     DEFAULT CURRENT_TIMESTAMP,
    is_active      TINYINT(1)   DEFAULT 1,
    department     VARCHAR(50)  NOT NULL,
    year           INT          NOT NULL,
    semester       INT          NOT NULL
);

-- ── Attendance ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS attendance (
    id            INT          AUTO_INCREMENT PRIMARY KEY,
    student_id    VARCHAR(20)  NOT NULL,
    date          DATE         NOT NULL,
    time_in       DATETIME     NOT NULL,
    status        ENUM('ON TIME','LATE','ABSENT') NOT NULL,
    minutes_late  INT          DEFAULT 0,
    device_id     VARCHAR(100),
    ip_address    VARCHAR(45),
    auth_method   ENUM('QR','QR+FACE','MANUAL','GPS') DEFAULT 'QR+FACE',
    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
    UNIQUE KEY uq_student_date (student_id, date)
);

-- ── Behavior Analytics Cache ────────────────────────────────
CREATE TABLE IF NOT EXISTS behavior_stats (
    id               INT    AUTO_INCREMENT PRIMARY KEY,
    student_id       VARCHAR(20) NOT NULL UNIQUE,
    total_classes    INT    DEFAULT 0,
    present_count    INT    DEFAULT 0,
    late_count       INT    DEFAULT 0,
    absent_count     INT    DEFAULT 0,
    late_pct         FLOAT  DEFAULT 0.0,
    absent_pct       FLOAT  DEFAULT 0.0,
    avg_minutes_late FLOAT  DEFAULT 0.0,
    max_absent_streak INT   DEFAULT 0,
    risk_level       ENUM('LOW','MEDIUM','HIGH') DEFAULT 'LOW',
    absence_prob     FLOAT  DEFAULT 0.0,
    late_prob        FLOAT  DEFAULT 0.0,
    last_updated     DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE
);

-- ── Alerts ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS alerts (
    id           INT          AUTO_INCREMENT PRIMARY KEY,
    student_id   VARCHAR(20)  NOT NULL,
    alert_type   ENUM('LATE_STREAK','ABSENT_STREAK','PROXY_ATTEMPT',
                      'GEO_FENCE','RISK_HIGH','PREDICTION') NOT NULL,
    severity     ENUM('INFO','WARNING','CRITICAL') DEFAULT 'WARNING',
    message      TEXT,
    triggered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_read      TINYINT(1) DEFAULT 0,
    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE
);

-- ── System Logs ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS system_logs (
    id        BIGINT  AUTO_INCREMENT PRIMARY KEY,
    event     VARCHAR(100) NOT NULL,
    details   TEXT,
    level     ENUM('DEBUG','INFO','WARNING','ERROR') DEFAULT 'INFO',
    logged_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ── Indexes for performance ──────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_att_date      ON attendance(date);
CREATE INDEX IF NOT EXISTS idx_att_status    ON attendance(status);
CREATE INDEX IF NOT EXISTS idx_alert_student ON alerts(student_id);
CREATE INDEX IF NOT EXISTS idx_alert_unread  ON alerts(is_read);

-- ── Attendance Sessions ─────────────────────────────────────
CREATE TABLE IF NOT EXISTS attendance_sessions (
    id           INT          AUTO_INCREMENT PRIMARY KEY,
    session_name VARCHAR(100) NOT NULL,
    teacher_id   VARCHAR(20)  NOT NULL,
    start_time   DATETIME     NOT NULL,
    end_time     DATETIME     NOT NULL,
    is_active    TINYINT(1)   DEFAULT 1,
    created_at   DATETIME     DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (teacher_id) REFERENCES teachers(teacher_id) ON DELETE CASCADE
);

-- ── Subject-Wise Performance Ratings ────────────────────────
CREATE TABLE IF NOT EXISTS student_ratings (
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
);

CREATE INDEX IF NOT EXISTS idx_rating_student ON student_ratings(student_id);
