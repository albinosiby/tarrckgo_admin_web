from flask import Blueprint, render_template, session, redirect, url_for
from app.services.firebase_service import get_db

routes_bp = Blueprint('routes', __name__)

SAMPLE_ROUTES = [
    {
        'id': 'sample_1',
        'route_name': 'Route 1 (Sample)',
        'start_point': 'Central Station',
        'end_point': 'University Campus',
        'stops': 'Main Square, City Park, Library',
        'assigned_bus': 'KL-11-AX-1234',
        'distance': '12 km'
    },
    {
        'id': 'sample_2',
        'route_name': 'Route 2 (Sample)',
        'start_point': 'North Terminal',
        'end_point': 'Tech Park',
        'stops': 'Hospital, Shopping Mall, Stadium',
        'assigned_bus': 'Unassigned',
        'distance': '8.5 km'
    }
]

@routes_bp.route('/routes')
def routes():
    if 'user' not in session: return redirect(url_for('auth.login'))
    uid = session.get('uid')
    db = get_db()
    routes_ref = db.collection('admins').document(uid).collection('routes')
    routes = []
    for doc in routes_ref.stream():
        route_data = doc.to_dict()
        route_data['id'] = doc.id
        routes.append(route_data)
    
    # Use sample data if no routes found
    if not routes:
        routes = SAMPLE_ROUTES
        
    return render_template('routes.html', routes=routes)

@routes_bp.route('/route/<route_id>')
def route_details(route_id):
    if 'user' not in session: return redirect(url_for('auth.login'))
    uid = session.get('uid')
    db = get_db()
    
    # Check if it's a sample route
    if route_id.startswith('sample_'):
        route = next((r for r in SAMPLE_ROUTES if r['id'] == route_id), None)
    else:
        route_ref = db.collection('admins').document(uid).collection('routes').document(route_id)
        route = route_ref.get().to_dict()
        if route:
            route['id'] = route_id
            
    # Fetch buses for dropdown
    buses_ref = db.collection('admins').document(uid).collection('buses')
    buses = []
    for doc in buses_ref.stream():
        b_data = doc.to_dict()
        b_data['id'] = doc.id
        buses.append(b_data)

    return render_template('route_details.html', route=route, buses=buses)

@routes_bp.route('/add_route')
def add_route():
    if 'user' not in session: return redirect(url_for('auth.login'))
    uid = session.get('uid')
    db = get_db()
    
    # Fetch buses for dropdown
    buses_ref = db.collection('admins').document(uid).collection('buses')
    buses = []
    for doc in buses_ref.stream():
        b_data = doc.to_dict()
        b_data['id'] = doc.id
        buses.append(b_data)
        
    return render_template('add_route.html', buses=buses)
