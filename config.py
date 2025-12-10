import os
import datetime

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your_fixed_secret_key_here_replace_in_production'
    PERMANENT_SESSION_LIFETIME = datetime.timedelta(days=30)
    # Prefer env var for credentials, fallback to file
    FIREBASE_CREDENTIALS = os.environ.get('FIREBASE_CREDENTIALS_JSON') or "serviceAccountKey.json"
    FIREBASE_RTDB_URL = "https://bus-management-c8612-default-rtdb.firebaseio.com/"
