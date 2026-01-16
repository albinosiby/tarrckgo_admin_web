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

    # Fetch Trip History (Top 10 only)
    trip_history = []
    latest_trip = None
    try:
        trips_ref = bus_ref.collection('trip_history').order_by('timestamp', direction=firestore.Query.DESCENDING).limit(10)
        trips_stream = list(trips_ref.stream())
        
        for t_doc in trips_stream:
            t_data = t_doc.to_dict()
            t_data['id'] = t_doc.id
            trip_history.append(t_data)
            
        if trip_history:
            latest_trip = trip_history[0]
    except Exception as e:
        print(f"Error fetching trip history: {e}")

    # Fetch all assigned students
    assigned_students = []
    try:
        students_ref = db.collection('organizations').document(uid).collection('students').where('bus_id', '==', bus_id)
        for s_doc in students_ref.stream():
            s_data = s_doc.to_dict()
            s_data['id'] = s_doc.id
            assigned_students.append(s_data)
    except Exception as e:
        print(f"Error fetching assigned students: {e}")

    # Fetch boarded students from 'boards' subcollection
    boarded_students = []
    try:
        # Fetch recent board logs (last 50 should be enough for a bus)
        boards_ref = bus_ref.collection('boards').order_by('timestamp', direction=firestore.Query.DESCENDING).limit(50)
        board_docs = list(boards_ref.stream())
        
        seen_students = set()
        
        for doc in board_docs:
            data = doc.to_dict()
            sid = data.get('studentId')
            
            if sid and sid not in seen_students:
                seen_students.add(sid)
                
                # Check if latest action is entry
                if data.get('scanType') == 'entry':
                    # Map fields to match template expectations
                    student_obj = {
                        'full_name': data.get('studentName', 'Unknown'),
                        'roll_number': data.get('rollNumber', '-'),
                        'parent_phone': data.get('parentPhone', '-'),
                        'profile_photo_url': data.get('photoUrl'),
                        'boarding_time': data.get('timestamp') # Optional, for debug/display
                    }
                    boarded_students.append(student_obj)
                    
    except Exception as e:
        print(f"Error fetching boards from subcollection: {e}")

    # Fetch drivers (Filter out those assigned to OTHER buses)
    drivers_ref = db.collection('organizations').document(uid).collection('drivers')
    drivers = []
    for doc in drivers_ref.stream():
        d_data = doc.to_dict()
        d_data['id'] = doc.id
        
        # Include if unassigned OR assigned to THIS bus
        assigned_bus = d_data.get('assigned_bus')
        if not assigned_bus or assigned_bus == bus_id:
            drivers.append(d_data)

    # Fetch routes (Filter out those assigned to OTHER buses)
    routes_ref = db.collection('organizations').document(uid).collection('routes')
    routes = []
    for doc in routes_ref.stream():
        r_data = doc.to_dict()
        r_data['id'] = doc.id
        
        # Include if unassigned OR assigned to THIS bus
        assigned_bus_route = r_data.get('assigned_bus')
        if not assigned_bus_route or assigned_bus_route == bus_id:
            routes.append(r_data)

    return render_template('bus_details.html', bus=bus, drivers=drivers, routes=routes, trip_history=trip_history, boarded_students=boarded_students, assigned_students=assigned_students)

@buses_bp.route('/bus/<bus_id>/history')
def bus_trip_history(bus_id):
    if 'user' not in session: return redirect(url_for('auth.login'))
    uid = session.get('uid')
    db = get_db()
    bus_ref = db.collection('organizations').document(uid).collection('buses').document(bus_id)
    bus = bus_ref.get().to_dict()
    if bus: bus['id'] = bus_id
    
    trip_history = []
    try:
        # Fetch ALL history (or reasonably large limit)
        trips_ref = bus_ref.collection('trip_history').order_by('timestamp', direction=firestore.Query.DESCENDING).limit(100)
        trips_stream = trips_ref.stream()
        
        for t_doc in trips_stream:
            t_data = t_doc.to_dict()
            t_data['id'] = t_doc.id
            trip_history.append(t_data)
    except Exception as e:
        print(f"Error fetching full trip history: {e}")
        
    return render_template('bus_trip_history.html', bus=bus, trip_history=trip_history)

@buses_bp.route('/add_bus')
def add_bus():
    if 'user' not in session: return redirect(url_for('auth.login'))
    uid = session.get('uid')
    db = get_db()

    # Fetch drivers (Only unassigned)
    drivers_ref = db.collection('organizations').document(uid).collection('drivers')
    drivers = []
    for doc in drivers_ref.stream():
        d_data = doc.to_dict()
        d_data['id'] = doc.id
        if not d_data.get('assigned_bus'):
            drivers.append(d_data)

    # Fetch routes (Only unassigned)
    routes_ref = db.collection('organizations').document(uid).collection('routes')
    routes = []
    for doc in routes_ref.stream():
        r_data = doc.to_dict()
        r_data['id'] = doc.id
        if not r_data.get('assigned_bus'):
            routes.append(r_data)

    return render_template('add_bus.html', drivers=drivers, routes=routes)
