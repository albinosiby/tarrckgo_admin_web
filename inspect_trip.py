
import os
import sys

# Add the project directory to sys.path
sys.path.append(os.getcwd())

from app import create_app
from app.services.firebase_service import get_db
from firebase_admin import firestore

app = create_app()

with app.app_context():
    db = get_db()
    
    # Get the first organization
    orgs = list(db.collection('organizations').limit(1).stream())
    if not orgs:
        print("No organizations found.")
        sys.exit()
    uid = orgs[0].id
    
    # Get the first bus
    buses = list(db.collection('organizations').document(uid).collection('buses').limit(1).stream())
    if not buses:
        print("No buses found.")
        sys.exit()
    bus = buses[0]
    
    print(f"Bus: {bus.id}")
    
    # Get latest trip
    trips = list(bus.reference.collection('trip_history').order_by('timestamp', direction=firestore.Query.DESCENDING).limit(1).stream())
    if trips:
        trip = trips[0]
        t_data = trip.to_dict()
        print("Latest Trip Keys:", list(t_data.keys()))
        print("Latest Trip Data:", t_data)
    else:
        print("No trips found.")
