from flask import Blueprint, render_template, redirect, url_for, session, request, jsonify
from firebase_admin import auth

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login')
def login():
    if 'user' in session:
        return redirect(url_for('main.index'))
    return render_template('login.html')

@auth_bp.route('/session_login', methods=['POST'])
def session_login():
    data = request.get_json()
    id_token = data.get('idToken')
    
    try:
        decoded_token = auth.verify_id_token(id_token, clock_skew_seconds=10)
        session['user'] = decoded_token['email']
        session['uid'] = decoded_token['uid']
        
        remember_me = data.get('rememberMe', False)
        if remember_me:
            session.permanent = True
            
        return jsonify({'status': 'success'})
    except Exception as e:
        print(f"Error verifying token: {e}")
        return jsonify({'status': 'error', 'message': 'Invalid token'}), 401

@auth_bp.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('auth.login'))
