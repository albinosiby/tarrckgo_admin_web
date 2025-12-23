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

    # Fetch boarded students if there is an active trip
    boarded_students = []
    trip_status = latest_trip.get('status', '').lower() if latest_trip else ''
    if latest_trip and trip_status in ['started', 'tripstarted', 'ongoing']:
        try:
             student_ids = []
             # Option 1: Check for explicit list in trip doc
             if 'boarded_student_ids' in latest_trip:
                 student_ids = latest_trip.get('boarded_student_ids', [])
             
             # Option 2: If no list, check for 'scans' map/list
             if not student_ids and 'scans' in latest_trip:
                 scans = latest_trip.get('scans')
                 if isinstance(scans, list):
                     for s in scans:
                         # Handle both snake_case and camelCase
                         sid = s.get('cardId') or s.get('studentId')
                         stype = s.get('scanType')
                         
                         if stype == 'entry':
                             student_ids.append(sid)
                         elif stype == 'exit':
                             if sid in student_ids:
                                 student_ids.remove(sid)
                 elif isinstance(scans, dict):
                     for k, v in scans.items():
                         # Handle both snake_case and camelCase
                         sid = v.get('cardId') or v.get('studentId')
                         stype = v.get('scanType')
                         
                         if stype == 'entry':
                             student_ids.append(sid)
                         elif stype == 'exit':
                             if sid in student_ids:
                                 student_ids.remove(sid)

             print(f"[DEBUG] Bus {bus_id} Trip {latest_trip.get('id')} Status: {trip_status}")
             print(f"[DEBUG] Raw IDs: {student_ids}")

             # Remove duplicates
             student_ids = list(set([str(sid) for sid in student_ids if sid]))

             if student_ids:
                 # 1. Check in assigned students first (avoid reads)
                 assigned_map = {str(s['id']): s for s in assigned_students}
                 # Also map by roll_number just in case
                 assigned_roll_map = {str(s.get('roll_number')): s for s in assigned_students if s.get('roll_number')}
                 
                 refs_to_fetch = []
                 fetched_ids = set()

                 for sid in student_ids:
                     found_student = None
                     if sid in assigned_map:
                         found_student = assigned_map[sid]
                     elif sid in assigned_roll_map:
                         found_student = assigned_roll_map[sid]
                     
                     if found_student:
                         if found_student['id'] not in fetched_ids:
                             s_data = found_student.copy()
                             s_data['boarding_status'] = 'On Board'
                             boarded_students.append(s_data)
                             fetched_ids.add(found_student['id'])
                     else:
                         # Fallback: Student might not be assigned or ID mismatch
                         # Try querying by roll_number or rfid_tag_id
                         try:
                             # Try fetching by ID first (if valid ID)
                             s_doc_ref = db.collection('organizations').document(uid).collection('students').document(sid)
                             s_snap = s_doc_ref.get()
                             
                             if s_snap.exists:
                                 found_student = s_snap.to_dict()
                                 found_student['id'] = s_snap.id
                             else:
                                 # Query by roll_number
                                 query = db.collection('organizations').document(uid).collection('students').where('roll_number', '==', sid).limit(1)
                                 query_snaps = list(query.stream())
                                 if query_snaps:
                                     found_student = query_snaps[0].to_dict()
                                     found_student['id'] = query_snaps[0].id
                                 else:
                                     # Query by rfid_tag_id
                                     query_rfid = db.collection('organizations').document(uid).collection('students').where('rfid_tag_id', '==', sid).limit(1)
                                     rfid_snaps = list(query_rfid.stream())
                                     if rfid_snaps:
                                         found_student = rfid_snaps[0].to_dict()
                                         found_student['id'] = rfid_snaps[0].id

                             if found_student and found_student.get('id') not in fetched_ids:
                                  s_data = found_student.copy()
                                  s_data['boarding_status'] = 'On Board'
                                  boarded_students.append(s_data)
                                  fetched_ids.add(found_student['id'])
                                  
                         except Exception as e:
                             print(f"Error resolving student {sid}: {e}")

        except Exception as e:
             print(f"Error fetching boarded students: {e}")

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
