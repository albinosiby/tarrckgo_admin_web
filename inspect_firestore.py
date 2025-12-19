
from app.services.firebase_service import get_db
from flask import Flask
from firebase_admin import credentials, firestore, initialize_app
import os

# Mocking the app setup to use the service
# We need to manually initialize if not running via the app, 
# but the user's environment seems to have app set up.
# We'll try to use the existing app structure if possible, or just raw firestore.

# Assuming credentials are set up in the environment or default
# We can try to import create_app or similar if available, or just use the service.

from main import app # standard entry point often

with app.app_context():
    db = get_db()
    # Need a UID. We can list organizations first.
    orgs = list(db.collection('organizations').limit(1).stream())
    if orgs:
        uid = orgs[0].id
        print(f"Using Organization UID: {uid}")
        
        buses = list(db.collection('organizations').document(uid).collection('buses').limit(1).stream())
        if buses:
            bus = buses[0]
            print(f"Bus ID: {bus.id}")
            print(f"Bus Data Keys: {bus.to_dict().keys()}")
            
            # List subcollections
            print("Subcollections:")
            for coll in bus.reference.collections():
                print(f" - {coll.id}")
                
            # If 'boarded_students' or similar exists, show a doc
            # If 'trip_history' exists, show keys of a doc
            
        else:
            print("No buses found.")
    else:
        print("No organizations found.")
