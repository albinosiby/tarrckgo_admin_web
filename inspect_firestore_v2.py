
import os
import sys

# Add the project directory to sys.path
sys.path.append(os.getcwd())

from app import create_app
from app.services.firebase_service import get_db

app = create_app()

with app.app_context():
    db = get_db()
    
    # Get the first organization
    orgs = list(db.collection('organizations').limit(1).stream())
    if not orgs:
        print("No organizations found.")
        sys.exit()
        
    uid = orgs[0].id
    print(f"Organization ID: {uid}")
    
    # Get the first bus
    buses = list(db.collection('organizations').document(uid).collection('buses').limit(1).stream())
    if not buses:
        print("No buses found.")
        sys.exit()
        
    bus = buses[0]
    bus_data = bus.to_dict()
    print(f"Bus ID: {bus.id}")
    print("Bus Keys:", list(bus_data.keys()))
    
    if 'on_board_count' in bus_data:
        print(f"On Board Count: {bus_data['on_board_count']}")

    print("\n--- Subcollections ---")
    collections = bus.reference.collections()
    for coll in collections:
        print(f"Subcollection: {coll.id}")
        # Peek into subcollection
        docs = list(coll.limit(1).stream())
        if docs:
            print(f"  Sample Doc ID: {docs[0].id}")
            print(f"  Sample Doc Keys: {list(docs[0].to_dict().keys())}")
            if coll.id == 'trip_history':
                # detailed peek
                print(f"  Trip Data: {docs[0].to_dict()}")
