
import json
import firebase_admin
from firebase_admin import firestore
from datetime import datetime
from app import create_app
from app.services.firebase_service import get_db

# Custom JSON encoder for datetime objects
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super(DateTimeEncoder, self).default(obj)

def fetch_collection_data(collection_ref):
    """
    Recursively fetch data from a collection and its subcollections.
    """
    data = {}
    docs = list(collection_ref.stream())
    
    for doc in docs:
        doc_data = doc.to_dict()
        doc_id = doc.id
        
        # Recursively fetch subcollections
        subcollections = {}
        for subcollection in doc.reference.collections():
            subcollections[subcollection.id] = fetch_collection_data(subcollection)
            
        if subcollections:
            doc_data['_subcollections'] = subcollections
            
        data[doc_id] = doc_data
        
    return data

def main():
    app = create_app()
    with app.app_context():
        db = get_db()
        print("Connected to Firestore.")
        
        # We need to start from root collections. 
        # Firestore logic: db.collections() lists root collections.
        root_data = {}
        
        print("Fetching root collections...")
        # Note: db.collections() returns a generator of CollectionReference
        for collection in db.collections():
            print(f"Fetching collection: {collection.id}")
            root_data[collection.id] = fetch_collection_data(collection)
            
        output_file = 'firestore_export.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(root_data, f, cls=DateTimeEncoder, indent=4)
            
        print(f"Data exported to {output_file}")

if __name__ == "__main__":
    main()
