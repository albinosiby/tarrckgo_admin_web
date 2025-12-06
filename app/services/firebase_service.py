import firebase_admin
from firebase_admin import credentials, firestore

db = None

def init_firebase(app):
    global db
    if not firebase_admin._apps:
        cred = credentials.Certificate(app.config['FIREBASE_CREDENTIALS'])
        firebase_admin.initialize_app(cred)
    db = firestore.client()

def get_db():
    return db
