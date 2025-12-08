
from flask import Blueprint, render_template, session, redirect, url_for
from app.services.firebase_service import get_db

drivers_bp = Blueprint('drivers', __name__)

@drivers_bp.route('/drivers')
def drivers():
    if 'user' not in session: return redirect(url_for('auth.login'))
    uid = session.get('uid')
    db = get_db()
    drivers_ref = db.collection('organizations').document(uid).collection('drivers')
    drivers = []
    for doc in drivers_ref.stream():
        driver_data = doc.to_dict()
        driver_data['id'] = doc.id
        drivers.append(driver_data)
    return render_template('drivers.html', drivers=drivers)

@drivers_bp.route('/driver/<driver_id>')
def driver_details(driver_id):
    if 'user' not in session: return redirect(url_for('auth.login'))
    uid = session.get('uid')
    db = get_db()
    driver_ref = db.collection('organizations').document(uid).collection('drivers').document(driver_id)
    driver = driver_ref.get().to_dict()
    if driver:
        driver['id'] = driver_id

    # Fetch buses for dropdown
    buses_ref = db.collection('organizations').document(uid).collection('buses')
    buses = []
    for doc in buses_ref.stream():
        b_data = doc.to_dict()
        b_data['id'] = doc.id
        buses.append(b_data)

    return render_template('driver_details.html', driver=driver, buses=buses)

@drivers_bp.route('/add_driver')
def add_driver():
    if 'user' not in session: return redirect(url_for('auth.login'))
    return render_template('add_driver.html')
