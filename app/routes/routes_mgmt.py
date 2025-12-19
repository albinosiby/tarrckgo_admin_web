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
                # If not in map, it might be Unassigned or legacy name
                route['assigned_bus_name'] = bus_id if bus_id else 'Unassigned'

    return render_template('routes.html', routes=routes)

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

    return render_template('route_details.html', route=route, buses=buses)

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
