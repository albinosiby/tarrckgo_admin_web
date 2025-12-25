from flask import Blueprint, render_template, session, redirect, url_for
from app.services.firebase_service import get_db

routes_bp = Blueprint('routes', __name__)



@routes_bp.route('/routes')
def routes():
    if 'user' not in session: return redirect(url_for('auth.login'))
    uid = session.get('uid')
    db = get_db()
    routes_ref = db.collection('organizations').document(uid).collection('routes')
    routes = []
    for doc in routes_ref.stream():
        route_data = doc.to_dict()
        route_data['id'] = doc.id
        routes.append(route_data)
    
    # Use sample data if no routes found
    if not routes:
        pass # No routes, just empty list
    else:
        # Fetch buses to map IDs to Names
        buses_ref = db.collection('organizations').document(uid).collection('buses')
        bus_map = {}
        for b_doc in buses_ref.stream():
            b_data = b_doc.to_dict()
            # Map ID to Bus Number
            bus_map[b_doc.id] = b_data.get('bus_number', 'Unknown Bus')
            
        # Update routes with bus name
        for route in routes:
            bus_id = route.get('assigned_bus')
            # Check if bus_id exists and is in map (simple check if it looks like an ID)
            if bus_id and bus_id in bus_map:
                route['assigned_bus_name'] = bus_map[bus_id]
            else:
                route['assigned_bus_name'] = bus_id if bus_id else 'Unassigned'
                
    return render_template('routes.html', routes=routes)

@routes_bp.route('/stops')
def stops():
    if 'uid' not in session:
        return redirect(url_for('auth.login'))
    
    uid = session['uid']
    db = get_db()
    
    # Fetch all global stops
    stops_ref = db.collection('organizations').document(uid).collection('stops').order_by('stop_name')
    all_stops = []
    
    # Validation Helper: Fetch all students for name lookup
    students_ref = db.collection('organizations').document(uid).collection('students')
    student_map = {}
    for s in students_ref.stream():
        d = s.to_dict()
        student_map[s.id] = d.get('full_name', 'Unknown')

    for s_doc in stops_ref.stream():
        s_data = s_doc.to_dict()
        s_data['id'] = s_doc.id
        
        # Enrich assigned_students with names
        enriched_students = []
        raw_assigned = s_data.get('assigned_students', [])
        
        if raw_assigned and isinstance(raw_assigned, list):
            for roll in raw_assigned:
                if roll in student_map:
                    enriched_students.append({'roll': roll, 'name': student_map[roll]})
                else:
                    enriched_students.append({'roll': roll, 'name': 'Unknown'})
        
        s_data['assigned_students_details'] = enriched_students
        s_data['student_count'] = len(enriched_students)
        
        all_stops.append(s_data)

    return render_template('stops.html', all_stops=all_stops)

@routes_bp.route('/route/<route_id>')
def route_details(route_id):
    if 'user' not in session: return redirect(url_for('auth.login'))
    uid = session.get('uid')
    db = get_db()
    
    # Check if it's a sample route (REMOVED)
    if False: 
        pass
    else:
        route_ref = db.collection('organizations').document(uid).collection('routes').document(route_id)
        route = route_ref.get().to_dict()
        if route:
            route['id'] = route_id
            
    # Fetch buses for dropdown
    buses_ref = db.collection('organizations').document(uid).collection('buses')
    buses = []
    bus_map = {}
    for doc in buses_ref.stream():
        b_data = doc.to_dict()
        b_data['id'] = doc.id
        buses.append(b_data)
        bus_map[doc.id] = b_data.get('bus_number', 'Unknown')

    # Add assigned_bus_name
    if route:
        aid = route.get('assigned_bus')
        if aid and aid in bus_map:
            route['assigned_bus_name'] = bus_map[aid]
        else:
            route['assigned_bus_name'] = aid if aid else 'Unassigned'

    # Fetch global stops for adding to route
    stops_ref = db.collection('organizations').document(uid).collection('stops').order_by('stop_name')
    all_stops = []
    stop_map = {}
    for s_doc in stops_ref.stream():
        s_data = s_doc.to_dict()
        s_data['id'] = s_doc.id
        all_stops.append(s_data)
        stop_map[s_doc.id] = s_data

    # Enrich route stops with coordinates
    if route and 'stops' in route and isinstance(route['stops'], list):
        enriched_stops = []
        for stop in route['stops']:
            if isinstance(stop, dict) and 'id' in stop and stop['id'] in stop_map:
                full_stop = stop_map[stop['id']]
                stop['lat'] = full_stop.get('lat', 0)
                stop['long'] = full_stop.get('long', 0)
            enriched_stops.append(stop)
        
        # Sort stops by fee (ascending)
        # Handle cases where stop might be a string (legacy) or dict
        def get_fee(s):
            if isinstance(s, dict):
                try:
                    return float(s.get('fee', 0))
                except (ValueError, TypeError):
                    return 0.0
            return 0.0
            
        route['stops'] = sorted(enriched_stops, key=get_fee)

    # Find assigned bus data
    assigned_bus_data = None
    if route and route.get('assigned_bus'):
        for bus in buses:
            if bus['id'] == route['assigned_bus']:
                assigned_bus_data = bus
                break

    return render_template('route_details.html', route=route, buses=buses, all_stops=all_stops, assigned_bus=assigned_bus_data)

@routes_bp.route('/add_route')
def add_route():
    if 'user' not in session: return redirect(url_for('auth.login'))
    uid = session.get('uid')
    db = get_db()
    
    # Fetch buses for dropdown
    buses_ref = db.collection('organizations').document(uid).collection('buses')
    buses = []
    for doc in buses_ref.stream():
        b_data = doc.to_dict()
        b_data['id'] = doc.id
        buses.append(b_data)
        
    return render_template('add_route.html', buses=buses)
