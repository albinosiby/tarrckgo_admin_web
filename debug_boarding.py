
from app.services.firebase_service import get_db
from flask import Flask
from firebase_admin import firestore
import os
import sys

sys.path.append(os.getcwd())
from main import app

with app.app_context():
    db = get_db()
    orgs = list(db.collection('organizations').limit(1).stream())
    if not orgs:
        print("No organizations found.")
        sys.exit()
    
    uid = orgs[0].id
    print(f"Organization ID: {uid}")
    
    buses = list(db.collection('organizations').document(uid).collection('buses').limit(5).stream())
    
    found_scans = False
    
    for bus in buses:
        print(f"\nChecking Bus: {bus.id} ({bus.get('bus_number')})")
        
        # Get latest trip
        trips_ref = bus.reference.collection('trip_history').order_by('timestamp', direction=firestore.Query.DESCENDING).limit(1)
        trips = list(trips_ref.stream())
        
        if not trips:
            print("  No trip history.")
            continue
            
        latest_trip = trips[0].to_dict()
        trip_id = trips[0].id
        print(f"  Latest Trip ID: {trip_id}")
        print(f"  Trip Status: {latest_trip.get('status')}")
        
        scans = latest_trip.get('scans')
        if not scans:
            print("  No 'scans' field in this trip.")
            continue
            
        print(f"  Raw Scans Data: {scans}")
        found_scans = True
        
        # Simulate extraction
        student_ids_extracted = []
        if isinstance(scans, list):
             for s in scans:
                 # USER LOGIC
                 sid = s.get('cardId') or s.get('studentId')
                 stype = s.get('scanType')
                 print(f"    - Extracted: sid={sid}, stype={stype}")
                 if stype == 'entry':
                     student_ids_extracted.append(sid)
        elif isinstance(scans, dict):
             for k, v in scans.items():
                 # USER LOGIC
                 sid = v.get('cardId') or v.get('studentId')
                 stype = v.get('scanType')
                 print(f"    - Extracted: sid={sid}, stype={stype}")
                 if stype == 'entry':
                     student_ids_extracted.append(sid)
                     
        print(f"  IDs to Lookup: {student_ids_extracted}")
        
        # Lookup check
        students_coll_ref = db.collection('organizations').document(uid).collection('students')
        
        for sid in student_ids_extracted:
            if not sid: continue
            
            # 1. Try by Document ID
            doc_ref = students_coll_ref.document(sid)
            doc_snap = doc_ref.get()
            if doc_snap.exists:
                print(f"    [MATCH] Found by Document ID: {sid} -> {doc_snap.to_dict().get('name')}")
            else:
                print(f"    [FAIL] Not found by Document ID: {sid}")
                
            # 2. Try by Roll Number
            query = students_coll_ref.where('roll_number', '==', sid).limit(1).stream()
            q_list = list(query)
            if q_list:
                print(f"    [MATCH] Found by Roll Number: {sid} -> {q_list[0].to_dict().get('name')}")
            else:
                 print(f"    [FAIL] Not found by Roll Number: {sid}")
            
             # 3. Try by RFID Tag
            query_rfid = students_coll_ref.where('rfid_tag_id', '==', sid).limit(1).stream()
            q_rfid_list = list(query_rfid)
            if q_rfid_list:
                print(f"    [MATCH] Found by RFID Tag: {sid} -> {q_rfid_list[0].to_dict().get('name')}")
            else:
                 print(f"    [FAIL] Not found by RFID Tag: {sid}")

    if not found_scans:
        print("\nSUMMARY: No scans found in any checked buses/trips. Data might be missing or under a different key.")
