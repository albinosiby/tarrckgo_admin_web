
from flask import Blueprint, render_template, session, redirect, url_for
from app.services.firebase_service import get_db
from firebase_admin import firestore

drivers_bp = Blueprint('drivers', __name__)

@drivers_bp.route('/drivers')
def drivers():
    if 'user' not in session: return redirect(url_for('auth.login'))
    uid = session.get('uid')
    db = get_db()
    drivers_ref = db.collection('organizations').document(uid).collection('drivers')
    
    # Fetch buses for mapping
    buses_ref = db.collection('organizations').document(uid).collection('buses')
    bus_map = {}
    for b_doc in buses_ref.stream():
        b_data = b_doc.to_dict()
        bus_map[b_doc.id] = b_data.get('bus_number', 'Unknown Bus')

    drivers = []
    for doc in drivers_ref.stream():
        driver_data = doc.to_dict()
        driver_data['id'] = doc.id
        
        # Map bus ID to name
        bid = driver_data.get('assigned_bus')
        if bid and bid in bus_map:
            driver_data['assigned_bus_name'] = bus_map[bid]
        else:
             driver_data['assigned_bus_name'] = bid if bid else 'Unassigned'
             
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

    # Fetch buses for dropdown and mapping
    buses_ref = db.collection('organizations').document(uid).collection('buses')
    buses = []
    bus_map = {}
    for doc in buses_ref.stream():
        b_data = doc.to_dict()
        b_data['id'] = doc.id
        buses.append(b_data)
        bus_map[doc.id] = b_data.get('bus_number', 'Unknown')
        
    if driver:
        bid = driver.get('assigned_bus')
        if bid and bid in bus_map:
            driver['assigned_bus_name'] = bus_map[bid]
        else:
            driver['assigned_bus_name'] = bid if bid else 'Unassigned'

    # Fetch Trip History
    # Strategy: Iterate all buses and find trips where driverId matches current driver
    # Note: This might be slow if there are many buses/trips. Ideally use CollectionGroup query if index exists.
    # We'll try manual aggregation for safety within org scope.
    trip_history = []
    try:
        # We already fetched buses above
        for bus_data in buses:
            bus_id = bus_data['id']
            bus_num = bus_data.get('bus_number', 'Unknown')
            
            # Query trip_history subcollection of this bus
            trips_ref = db.collection('organizations').document(uid).collection('buses').document(bus_id).collection('trip_history').where('driverId', '==', driver_id).order_by('timestamp', direction=firestore.Query.DESCENDING).limit(10)
            
            for t_doc in trips_ref.stream():
                t_data = t_doc.to_dict()
                t_data['id'] = t_doc.id
                t_data['bus_number'] = bus_num # Add bus number to display
                trip_history.append(t_data)
        
        # Sort combined results by timestamp desc
        trip_history.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
        
    except Exception as e:
        print(f"Error fetching driver trip history: {e}")

    return render_template('driver_details.html', driver=driver, buses=buses, trip_history=trip_history)

@drivers_bp.route('/add_driver')
def add_driver():
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

    return render_template('add_driver.html', buses=buses)
