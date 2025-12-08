from flask import Blueprint, render_template, session, redirect, url_for
from app.services.firebase_service import get_db

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    if 'user' not in session:
        return redirect(url_for('auth.login'))
    
    uid = session.get('uid')
    db = get_db()
    org_ref = db.collection('organizations').document(uid)
    org_doc = org_ref.get()
    org_name = 'Smart Bus Admin'
    if org_doc.exists:
        org_data = org_doc.to_dict()
        org_name = org_data.get('name', 'Smart Bus Admin')
        
    return render_template('index.html', org_name=org_name)

@main_bp.route('/profile')
def profile():
    if 'user' not in session: return redirect(url_for('auth.login'))
    uid = session.get('uid')
    db = get_db()
    org_ref = db.collection('organizations').document(uid)
    org_doc = org_ref.get()
    org = org_doc.to_dict() if org_doc.exists else {}
    return render_template('profile.html', org=org)

@main_bp.route('/settings')
def settings():
    if 'user' not in session: return redirect(url_for('auth.login'))
    return render_template('settings.html')

@main_bp.route('/tracking')
def tracking():
    if 'user' not in session: return redirect(url_for('auth.login'))
    return render_template('tracking.html')

@main_bp.route('/attendance')
def attendance():
    if 'user' not in session: return redirect(url_for('auth.login'))
    return render_template('attendance.html')
