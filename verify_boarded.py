
from app.services.firebase_service import get_db
from flask import Flask, render_template
from firebase_admin import credentials, firestore, initialize_app
import os
import sys

# Add the current directory to sys.path so we can import from app
sys.path.append(os.getcwd())

from main import app
from app.routes.buses import buses_bp 

# Mock request context? Or just call the logic directly?
# Since `bus_details` returns a template, we can't easily check the context variable `boarded_students` without parsing HTML or mocking render_template.
# Better to copy-paste the logic or make a testable function.
# But for now, let's just use the `inspect_scans_v2` approach but ALSO try to run the logic snippet.

with app.app_context():
    db = get_db()
    
    # 1. Find a bus with a recent trip
    uid = 'albinosiby' # Hardcoded or fetch
    
    try:
        orgs = list(db.collection('organizations').limit(1).stream())
        if orgs: 
            uid = orgs[0].id
    except:
        pass
        
    print(f"Using Organization UID: {uid}")
    
    buses_ref = db.collection('organizations').document(uid).collection('buses')
    buses = list(buses_ref.limit(5).stream())
    
    for bus_doc in buses:
        bus_id = bus_doc.id
        print(f"\nChecking Bus: {bus_id}")
        
        # Latest trip
        trips_ref = bus_doc.reference.collection('trip_history').order_by('timestamp', direction=firestore.Query.DESCENDING).limit(1)
        trips = list(trips_ref.stream())
        
        if not trips:
            print("  No trips found.")
            continue
            
        latest_trip = trips[0].to_dict()
        latest_trip['id'] = trips[0].id
        print(f"  Latest Trip: {latest_trip['id']} Status: {latest_trip.get('status')}")
        
        # Logic from buses.py
        boarded_students = []
        trip_status = latest_trip.get('status', '').lower() if latest_trip else ''
        
        # Simulate the check
        if latest_trip and trip_status in ['started', 'tripstarted', 'ongoing', 'allowed']: # 'allowed' is scan status, but checking if trip status might have issues
            # The logic in buses.py checks trip_status against ['started', 'tripstarted', 'ongoing']
            pass
            
        student_ids = []
        if 'scans' in latest_trip:
             scans = latest_trip.get('scans')
             print(f"  Scans (Raw): {scans}")
             if isinstance(scans, list):
                 for s in scans:
                     # Handle both snake_case and camelCase
                     sid = s.get('student_id') or s.get('studentId')
                     stype = s.get('type') or s.get('scanType')
                     
                     if stype == 'entry':
                         student_ids.append(sid)
                     elif stype == 'exit':
                         if sid in student_ids:
                             student_ids.remove(sid)
             elif isinstance(scans, dict):
                 for k, v in scans.items():
                     # Handle both snake_case and camelCase
                     sid = v.get('student_id') or v.get('studentId')
                     stype = v.get('type') or v.get('scanType')
                     
                     if stype == 'entry':
                         student_ids.append(sid)
                     elif stype == 'exit':
                         if sid in student_ids:
                             student_ids.remove(sid)
                             
        print(f"  Calculated Boarded IDs: {student_ids}")
        if student_ids:
            print("  SUCCESS: Found boarded students.")
        else:
            print("  No boarded students found (or logic failed if scans exist).")

