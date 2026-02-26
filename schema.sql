-- ================================================
-- NFC Student Attendance System - Database Schema
-- ================================================

CREATE DATABASE IF NOT EXISTS nfc_attendance;
USE nfc_attendance;

-- Students Table
CREATE TABLE IF NOT EXISTS students (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id VARCHAR(20) UNIQUE NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    course VARCHAR(100) NOT NULL,
    year INT NOT NULL,
    card_uid VARCHAR(50) UNIQUE,
    email VARCHAR(100),
    phone VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- Attendance Table
CREATE TABLE IF NOT EXISTS attendance (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id VARCHAR(20) NOT NULL,
    date DATE NOT NULL,
    time_in TIME,
    time_out TIME,
    duration_minutes INT,
    entry_point VARCHAR(50) DEFAULT 'main',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE
);

-- Admin Users Table
CREATE TABLE IF NOT EXISTS admin_users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    role ENUM('super_admin', 'admin', 'viewer') DEFAULT 'admin',
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Scan Logs Table (audit trail)
CREATE TABLE IF NOT EXISTS scan_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    card_uid VARCHAR(50),
    student_id VARCHAR(20),
    action VARCHAR(20),
    status VARCHAR(20),
    message TEXT,
    entry_point VARCHAR(50) DEFAULT 'main',
    scanned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ================================================
-- Sample Data
-- ================================================

-- Default admin (password: Admin@1234)
INSERT INTO admin_users (username, password_hash, full_name, role) VALUES
('admin', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMqJqhcanFp8RrB0rQwDqFRzHu', 'System Administrator', 'super_admin');

-- Sample Students
INSERT INTO students (student_id, full_name, course, year, card_uid, email) VALUES
('STU2026001', 'Kevin Ssemwanga', 'BSc Computer Science', 2, '04A3F91B2C', 'kevin.ssemwanga@university.ac.ug'),
('STU2026002', 'Aisha Nakato', 'BBA', 1, '039BD4827F', 'aisha.nakato@university.ac.ug');

-- Sample Attendance (past records)
INSERT INTO attendance (student_id, date, time_in, time_out, duration_minutes) VALUES
('STU2026001', CURDATE() - INTERVAL 1 DAY, '08:05:00', '16:30:00', 505),
('STU2026002', CURDATE() - INTERVAL 1 DAY, '08:15:00', '15:45:00', 450),
('STU2026001', CURDATE() - INTERVAL 2 DAY, '07:58:00', '16:00:00', 482),
('STU2026002', CURDATE() - INTERVAL 2 DAY, '09:00:00', '14:30:00', 330);

-- Indexes for performance
CREATE INDEX idx_attendance_student_date ON attendance(student_id, date);
CREATE INDEX idx_attendance_date ON attendance(date);
CREATE INDEX idx_students_card_uid ON students(card_uid);
