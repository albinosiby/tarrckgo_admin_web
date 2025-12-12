from flask import Blueprint, render_template, session, redirect, url_for
from app.services.firebase_service import get_db

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    if 'user' not in session:
        return redirect(url_for('auth.login'))
    
    uid = session.get('uid')
    db = get_db()
    org_ref = db.collection('organizations').document(uid)
    org_doc = org_ref.get()
    org_name = 'Smart Bus Admin'
    if org_doc.exists:
        org_data = org_doc.to_dict()
        org_name = org_data.get('name', 'Smart Bus Admin')

    # Fetch Routes for mapping
    routes_ref = org_ref.collection('routes')
    route_map = {}
    for r in routes_ref.stream():
        rd = r.to_dict()
        route_map[r.id] = rd.get('route_name', 'Unknown Route')

    # Fetch Buses
    buses_ref = org_ref.collection('buses')
    buses = []
    
    # Fetch Students for count
    students_ref = org_ref.collection('students')
    # Simple count for students (efficient enough for small datasets)
    # For large datasets, use aggregation queries or counters.
    total_students = len(list(students_ref.stream())) 
    
    # Fetch Drivers for count
    drivers_ref = org_ref.collection('drivers')
    total_drivers = len(list(drivers_ref.stream()))

    for b in buses_ref.stream():
        bus = b.to_dict()
        bus['id'] = b.id
        # Map route name
        r_id = bus.get('route_id')
        if r_id and r_id in route_map:
            bus['route_name'] = route_map[r_id]
        else:
            bus['route_name'] = 'No Route Assigned'
        
        buses.append(bus)

    active_buses_count = len(buses)
    
    # Placeholder for present_today until global attendance is implemented
    present_today = 0
        
    return render_template('index.html', org_name=org_name,
                           total_students=total_students,
                           active_buses=active_buses_count,
                           total_drivers=total_drivers,
                           present_today=present_today,
                           buses=buses)

@main_bp.route('/profile')
def profile():
    if 'user' not in session: return redirect(url_for('auth.login'))
    uid = session.get('uid')
    db = get_db()
    org_ref = db.collection('organizations').document(uid)
    org_doc = org_ref.get()
    org = org_doc.to_dict() if org_doc.exists else {}
    return render_template('profile.html', org=org)

@main_bp.route('/settings')
def settings():
    if 'user' not in session: return redirect(url_for('auth.login'))
    return render_template('settings.html')

@main_bp.route('/tracking')
def tracking():
    if 'user' not in session: return redirect(url_for('auth.login'))
    return render_template('tracking.html')

@main_bp.route('/attendance')
def attendance():
    if 'user' not in session: return redirect(url_for('auth.login'))
    return render_template('attendance.html')
