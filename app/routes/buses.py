from flask import Blueprint, render_template, session, redirect, url_for
from app.services.firebase_service import get_db
from firebase_admin import firestore

buses_bp = Blueprint('buses', __name__)

@buses_bp.route('/buses')
def buses():
    if 'user' not in session: return redirect(url_for('auth.login'))
    uid = session.get('uid')
    db = get_db()
    buses_ref = db.collection('organizations').document(uid).collection('buses')
    # Fetch drivers for mapping
    drivers_ref = db.collection('organizations').document(uid).collection('drivers')
    driver_map = {}
    for d_doc in drivers_ref.stream():
        d_data = d_doc.to_dict()
        driver_map[d_doc.id] = d_data.get('full_name', 'Unknown Driver')

    buses = []
    for doc in buses_ref.stream():
        bus_data = doc.to_dict()
        bus_data['id'] = doc.id
        
        # Map driver ID to name
        did = bus_data.get('driver_id')
        if did and did in driver_map:
            bus_data['driver_name_display'] = driver_map[did]
        else:
             bus_data['driver_name_display'] = bus_data.get('driver_name') if bus_data.get('driver_name') else 'Unassigned'
             
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
    # Fetch drivers for mapping
    drivers_ref = db.collection('organizations').document(uid).collection('drivers')
    driver_map = {}
    for d_doc in drivers_ref.stream():
        d_data = d_doc.to_dict()
        driver_map[d_doc.id] = d_data.get('full_name', 'Unknown Driver')

    if bus:
        bus['id'] = bus_id
        # Map driver ID to name
        did = bus.get('driver_id')
        if did and did in driver_map:
            bus['driver_name_display'] = driver_map[did]
        else:
             bus['driver_name_display'] = bus.get('driver_name') if bus.get('driver_name') else 'Unassigned'

    # Fetch Trip History
    trip_history = []
    try:
        trips_ref = bus_ref.collection('trip_history').order_by('timestamp', direction=firestore.Query.DESCENDING)
        for t_doc in trips_ref.stream():
            t_data = t_doc.to_dict()
            t_data['id'] = t_doc.id
            trip_history.append(t_data)
    except Exception as e:
        print(f"Error fetching trip history: {e}")

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

    return render_template('bus_details.html', bus=bus, drivers=drivers, routes=routes, trip_history=trip_history)

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
