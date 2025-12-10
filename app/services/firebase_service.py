import firebase_admin
from firebase_admin import credentials, firestore

db = None

import json

def init_firebase(app):
    global db
    if not firebase_admin._apps:
        creds_config = app.config['FIREBASE_CREDENTIALS']
        
        if isinstance(creds_config, dict):
            # Already a dict (unlikely from config but possible)
            cred = credentials.Certificate(creds_config)
        elif creds_config.startswith('{'):
            # It's a JSON string from env var
            cred_dict = json.loads(creds_config)
            cred = credentials.Certificate(cred_dict)
        else:
            # It's a file path
            cred = credentials.Certificate(creds_config)
            
        options = {
            'storageBucket': f"{cred.project_id}.firebasestorage.app",
            'databaseURL': app.config.get('FIREBASE_RTDB_URL')
        }
        firebase_admin.initialize_app(cred, options)
    db = firestore.client()

from firebase_admin import db as rtdb
from firebase_admin import storage

def get_bucket():
    return storage.bucket()

def get_db_rtdb():
    return rtdb

def get_db():
    return db
