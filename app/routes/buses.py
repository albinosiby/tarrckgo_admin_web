from flask import Blueprint, render_template, session, redirect, url_for
from app.services.firebase_service import get_db

buses_bp = Blueprint('buses', __name__)

@buses_bp.route('/buses')
def buses():
    if 'user' not in session: return redirect(url_for('auth.login'))
    uid = session.get('uid')
    db = get_db()
    buses_ref = db.collection('organizations').document(uid).collection('buses')
    buses = []
    for doc in buses_ref.stream():
        bus_data = doc.to_dict()
        bus_data['id'] = doc.id
        buses.append(bus_data)

    # Fetch drivers
    drivers_ref = db.collection('organizations').document(uid).collection('drivers')
    drivers = []
    for doc in drivers_ref.stream():
        d_data = doc.to_dict()
        d_data['id'] = doc.id
        drivers.append(d_data)

    # Fetch routes
    routes_ref = db.collection('organizations').document(uid).collection('routes')
    routes = []
    for doc in routes_ref.stream():
        r_data = doc.to_dict()
        r_data['id'] = doc.id
        routes.append(r_data)

    return render_template('buses.html', buses=buses, drivers=drivers, routes=routes)

@buses_bp.route('/bus/<bus_id>')
def bus_details(bus_id):
    if 'user' not in session: return redirect(url_for('auth.login'))
    uid = session.get('uid')
    db = get_db()
    bus_ref = db.collection('organizations').document(uid).collection('buses').document(bus_id)
    bus = bus_ref.get().to_dict()
    if bus:
        bus['id'] = bus_id

    # Fetch drivers
    drivers_ref = db.collection('organizations').document(uid).collection('drivers')
    drivers = []
    for doc in drivers_ref.stream():
        d_data = doc.to_dict()
        d_data['id'] = doc.id
        drivers.append(d_data)

    # Fetch routes
    routes_ref = db.collection('organizations').document(uid).collection('routes')
    routes = []
    for doc in routes_ref.stream():
        r_data = doc.to_dict()
        r_data['id'] = doc.id
        routes.append(r_data)

    return render_template('bus_details.html', bus=bus, drivers=drivers, routes=routes)

@buses_bp.route('/add_bus')
def add_bus():
    if 'user' not in session: return redirect(url_for('auth.login'))
    uid = session.get('uid')
    db = get_db()

    # Fetch drivers
    drivers_ref = db.collection('organizations').document(uid).collection('drivers')
    drivers = []
    for doc in drivers_ref.stream():
        d_data = doc.to_dict()
        d_data['id'] = doc.id
        drivers.append(d_data)

    # Fetch routes
    routes_ref = db.collection('organizations').document(uid).collection('routes')
    routes = []
    for doc in routes_ref.stream():
        r_data = doc.to_dict()
        r_data['id'] = doc.id
        routes.append(r_data)

    return render_template('add_bus.html', drivers=drivers, routes=routes)
