
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
    if not orgs: raise Exception("No organizations")
    uid = orgs[0].id
    
    # 1. Simulate the logic from buses.py
    print("Testing student lookup logic...")
    sid = "vml22cs031" # The ID from the user complaint
    
    # Try finding it
    print(f"Looking for student with ID/Roll: {sid}")
    
    found_student = None
    # 1. Direct fetch (simulate document(sid))
    doc_ref = db.collection('organizations').document(uid).collection('students').document(sid)
    snap = doc_ref.get()
    if snap.exists:
        print("  [SUCCESS] Found by Document ID")
        found_student = snap.to_dict()
    else:
        print("  [FAIL] Document ID match failed")
        
        # 2. Query Roll Number
        q = db.collection('organizations').document(uid).collection('students').where('roll_number', '==', sid).limit(1)
        snaps = list(q.stream())
        if snaps:
            print(f"  [SUCCESS] Found by Roll Number. ID: {snaps[0].id}")
            found_student = snaps[0].to_dict()
        else:
             print("  [FAIL] Roll Number match failed")
             
             # 3. Query RFID
             q_rfid = db.collection('organizations').document(uid).collection('students').where('rfid_tag_id', '==', sid).limit(1)
             snaps_rfid = list(q_rfid.stream())
             if snaps_rfid:
                  print(f"  [SUCCESS] Found by RFID Tag. ID: {snaps_rfid[0].id}")
                  found_student = snaps_rfid[0].to_dict()
             else:
                  print("  [FAIL] RFID Tag match failed")

    if found_student:
        print(f"Match confirmed: {found_student.get('student_name', 'No Name')}")
    else:
        print("Student could not be resolved with current logic.")
