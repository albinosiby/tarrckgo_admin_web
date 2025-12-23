
from app.services.firebase_service import get_db
from flask import Flask
from firebase_admin import credentials, firestore, initialize_app
import os
import sys

# Add the current directory to sys.path so we can import from app
sys.path.append(os.getcwd())

from main import app

with app.app_context():
    db = get_db()
    orgs = list(db.collection('organizations').limit(1).stream())
    if orgs:
        uid = orgs[0].id
        print(f"Using Organization UID: {uid}")
        
        buses = list(db.collection('organizations').document(uid).collection('buses').limit(1).stream())
        if buses:
            bus = buses[0]
            print(f"Bus ID: {bus.id}")
            
            # Fetch latest trip history with scans
            trips = list(bus.reference.collection('trip_history').order_by('timestamp', direction=firestore.Query.DESCENDING).limit(5).stream())
            
            found_scan = False
            for trip in trips:
                data = trip.to_dict()
                print(f"Trip ID: {trip.id}, Status: {data.get('status')}")
                if 'scans' in data:
                    print(f"  Scans found in trip {trip.id}:")
                    scans = data['scans']
                    if isinstance(scans, list):
                        for scan in scans[:3]: # Print first 3
                            print(f"   - {scan}")
                    elif isinstance(scans, dict):
                         # If it's a map, print keys/values
                         for k, v in list(scans.items())[:3]:
                             print(f"   - {k}: {v}")
                    found_scan = True
                    break
                if 'boarded_student_ids' in data:
                     print(f"  Boarded IDs: {data['boarded_student_ids']}")

            if not found_scan:
                print("No scans found in recent trips.")
        else:
            print("No buses found.")
    else:
        print("No organizations found.")
