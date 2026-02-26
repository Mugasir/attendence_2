"""
Attendance routes - Clock in/out logic, reports, CSV export
"""

from flask import Blueprint, request, jsonify, make_response
from flask_jwt_extended import jwt_required
from models.db import query
from datetime import date, datetime
import csv
import io

attendance_bp = Blueprint('attendance', __name__)


@attendance_bp.route('/scan', methods=['POST'])
def scan_card():
    """
    Core NFC scan endpoint.
    Called by the NFC reader daemon when a card is tapped.
    No JWT required — it's called by local hardware service.
    """
    data = request.get_json()
    card_uid = data.get('card_uid', '').strip().upper()
    entry_point = data.get('entry_point', 'main')

    if not card_uid:
        return jsonify({'status': 'error', 'message': 'No card UID provided'}), 400

    # Log the scan attempt
    def log_scan(student_id, action, status, message):
        query(
            "INSERT INTO scan_logs (card_uid, student_id, action, status, message, entry_point) VALUES (%s,%s,%s,%s,%s,%s)",
            (card_uid, student_id, action, status, message, entry_point),
            commit=True
        )

    # Find student by card UID
    student = query(
        "SELECT * FROM students WHERE card_uid = %s AND is_active = 1",
        (card_uid,), fetchone=True
    )

    if not student:
        log_scan(None, 'scan', 'unknown', f'Unknown card: {card_uid}')
        return jsonify({
            'status': 'error',
            'message': 'Card not registered. Please contact admin.',
            'card_uid': card_uid
        }), 404

    today = date.today().isoformat()
    now_time = datetime.now().strftime('%H:%M:%S')

    # Check for open attendance record today
    open_record = query(
        "SELECT * FROM attendance WHERE student_id = %s AND date = %s AND time_out IS NULL",
        (student['student_id'], today), fetchone=True
    )

    if open_record:
        # Clock OUT
        time_in = datetime.strptime(str(open_record['time_in']), '%H:%M:%S')
        time_now = datetime.strptime(now_time, '%H:%M:%S')
        duration = int((time_now - time_in).total_seconds() / 60)

        query(
            "UPDATE attendance SET time_out = %s, duration_minutes = %s WHERE id = %s",
            (now_time, duration, open_record['id']),
            commit=True
        )

        log_scan(student['student_id'], 'clock_out', 'success',
                 f"Clocked out at {now_time}, duration {duration} min")

        return jsonify({
            'status': 'clock_out',
            'message': f"Goodbye, {student['full_name']}! See you tomorrow.",
            'student': {
                'student_id': student['student_id'],
                'full_name': student['full_name'],
                'course': student['course'],
                'year': student['year']
            },
            'time_in': str(open_record['time_in']),
            'time_out': now_time,
            'duration_minutes': duration
        })
    else:
        # Clock IN
        query(
            "INSERT INTO attendance (student_id, date, time_in) VALUES (%s, %s, %s)",
            (student['student_id'], today, now_time),
            commit=True
        )

        log_scan(student['student_id'], 'clock_in', 'success', f"Clocked in at {now_time}")

        return jsonify({
            'status': 'clock_in',
            'message': f"Welcome, {student['full_name']}!",
            'student': {
                'student_id': student['student_id'],
                'full_name': student['full_name'],
                'course': student['course'],
                'year': student['year']
            },
            'time_in': now_time
        })


@attendance_bp.route('/today', methods=['GET'])
@jwt_required()
def today_attendance():
    today = date.today().isoformat()
    records = query(
        """SELECT a.*, s.full_name, s.course, s.year 
           FROM attendance a 
           JOIN students s ON a.student_id = s.student_id
           WHERE a.date = %s 
           ORDER BY a.time_in DESC""",
        (today,), fetchall=True
    )
    return jsonify({'records': records, 'date': today, 'count': len(records)})


@attendance_bp.route('/report', methods=['GET'])
@jwt_required()
def attendance_report():
    date_from = request.args.get('date_from', date.today().isoformat())
    date_to = request.args.get('date_to', date.today().isoformat())
    student_id = request.args.get('student_id', '')

    sql = """SELECT a.*, s.full_name, s.course, s.year 
             FROM attendance a 
             JOIN students s ON a.student_id = s.student_id
             WHERE a.date BETWEEN %s AND %s"""
    params = [date_from, date_to]

    if student_id:
        sql += " AND a.student_id = %s"
        params.append(student_id)

    sql += " ORDER BY a.date DESC, a.time_in DESC"
    records = query(sql, tuple(params), fetchall=True)

    # Convert timedelta to string for JSON serialization
    for r in records:
        for field in ['time_in', 'time_out']:
            if r[field] is not None:
                r[field] = str(r[field])

    return jsonify({'records': records, 'count': len(records)})


@attendance_bp.route('/export', methods=['GET'])
@jwt_required()
def export_csv():
    date_from = request.args.get('date_from', date.today().isoformat())
    date_to = request.args.get('date_to', date.today().isoformat())

    records = query(
        """SELECT a.student_id, s.full_name, s.course, s.year, a.date, 
                  a.time_in, a.time_out, a.duration_minutes, a.entry_point
           FROM attendance a 
           JOIN students s ON a.student_id = s.student_id
           WHERE a.date BETWEEN %s AND %s
           ORDER BY a.date DESC, s.full_name""",
        (date_from, date_to), fetchall=True
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Student ID', 'Full Name', 'Course', 'Year', 'Date',
                     'Time In', 'Time Out', 'Duration (min)', 'Entry Point'])

    for r in records:
        writer.writerow([
            r['student_id'], r['full_name'], r['course'], r['year'],
            r['date'], r['time_in'], r['time_out'] or '',
            r['duration_minutes'] or '', r['entry_point']
        ])

    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename=attendance_{date_from}_{date_to}.csv'
    return response


@attendance_bp.route('/summary', methods=['GET'])
@jwt_required()
def attendance_summary():
    """Total hours per student for a date range."""
    date_from = request.args.get('date_from', date.today().replace(day=1).isoformat())
    date_to = request.args.get('date_to', date.today().isoformat())

    records = query(
        """SELECT a.student_id, s.full_name, s.course, s.year,
                  COUNT(a.id) as days_present,
                  SUM(a.duration_minutes) as total_minutes,
                  ROUND(SUM(a.duration_minutes)/60, 2) as total_hours
           FROM attendance a
           JOIN students s ON a.student_id = s.student_id
           WHERE a.date BETWEEN %s AND %s
           GROUP BY a.student_id, s.full_name, s.course, s.year
           ORDER BY total_hours DESC""",
        (date_from, date_to), fetchall=True
    )
    return jsonify({'records': records, 'date_from': date_from, 'date_to': date_to})
