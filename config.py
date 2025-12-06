import os
import datetime

class Config:
    SECRET_KEY = 'your_fixed_secret_key_here_replace_in_production'
    PERMANENT_SESSION_LIFETIME = datetime.timedelta(days=30)
    FIREBASE_CREDENTIALS = "serviceAccountKey.json"
