
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
    trip_history = []
    try:
        # Direct query to driver's trip_history subcollection
        trips_ref = driver_ref.collection('trip_history').order_by('timestamp', direction=firestore.Query.DESCENDING).limit(50)
        
        for t_doc in trips_ref.stream():
            t_data = t_doc.to_dict()
            
            # Map fields for template
            # Helper to format timestamp
            def format_ts(ts):
                if not ts: return '-'
                try:
                     # Convert to IST (UTC+5:30)
                    from datetime import timedelta, timezone
                    target_tz = timezone(timedelta(hours=5, minutes=30))
                    
                    # If it's a Firestore datetime (aware), convert it.
                    # If naive, assume UTC and convert.
                    if hasattr(ts, 'astimezone'):
                         ts_local = ts.astimezone(target_tz)
                         return ts_local.strftime('%I:%M %p')
                    return str(ts)
                except:
                    return str(ts)

            # Calculate duration if not present
            duration = t_data.get('durationMinutes')
            st_obj = t_data.get('start_time') or t_data.get('startTime')
            et_obj = t_data.get('end_time') or t_data.get('endTime')

            if not duration and st_obj and et_obj:
                try:
                    # Ensure they are datetime objects
                    import datetime
                    if not isinstance(st_obj, datetime.datetime) and hasattr(st_obj, 'to_datetime'):
                        st_obj = st_obj.to_datetime()
                    if not isinstance(et_obj, datetime.datetime) and hasattr(et_obj, 'to_datetime'):
                        et_obj = et_obj.to_datetime()
                    
                    if isinstance(st_obj, datetime.datetime) and isinstance(et_obj, datetime.datetime):
                        diff = et_obj - st_obj
                        duration = int(diff.total_seconds() / 60)
                except Exception as e:
                    print(f"Error calculating duration: {e}")

            # Map fields for template
            trip = {
                'id': t_doc.id,
                'date': t_data.get('date', '-'),
                'bus_number': t_data.get('busNumber', t_data.get('bus_number', '-')),
                'type': t_data.get('trip_type', t_data.get('type', '-')),
                'startTime': format_ts(st_obj),
                'endTime': format_ts(et_obj),
                'durationMinutes': duration if duration is not None else 0
            }
            trip_history.append(trip)
            
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
