from flask import Blueprint, render_template, session, redirect, url_for
from app.services.firebase_service import get_db

students_bp = Blueprint('students', __name__)

@students_bp.route('/students')
def students():
    if 'user' not in session: return redirect(url_for('auth.login'))
    uid = session.get('uid')
    db = get_db()
    students_ref = db.collection('admins').document(uid).collection('students')
    students = []
    for doc in students_ref.stream():
        student = doc.to_dict()
        student['id'] = doc.id
        students.append(student)
    return render_template('students.html', students=students)

@students_bp.route('/add_student')
def add_student():
    if 'user' not in session: return redirect(url_for('auth.login'))
    uid = session.get('uid')
    db = get_db()
    
    # Fetch buses
    buses_ref = db.collection('admins').document(uid).collection('buses')
    buses = []
    for doc in buses_ref.stream():
        b_data = doc.to_dict()
        b_data['id'] = doc.id
        buses.append(b_data)

    # Fetch routes
    routes_ref = db.collection('admins').document(uid).collection('routes')
    routes = []
    for doc in routes_ref.stream():
        r_data = doc.to_dict()
        r_data['id'] = doc.id
        routes.append(r_data)

    return render_template('add_student.html', buses=buses, routes=routes)

@students_bp.route('/student_details/<student_id>')
def student_details(student_id):
    if 'user' not in session: return redirect(url_for('auth.login'))
    uid = session.get('uid')
    db = get_db()
    student_ref = db.collection('admins').document(uid).collection('students').document(student_id)
    student = student_ref.get().to_dict()
    if student:
        student['id'] = student_id
        return render_template('student_details.html', student=student)
    else:
        return "Student not found", 404
