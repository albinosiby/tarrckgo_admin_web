from flask import Blueprint, request, session, jsonify
from app.services.firebase_service import get_db

api_bp = Blueprint('api', __name__)

@api_bp.route('/api/add_student', methods=['POST'])
def api_add_student():
    if 'user' not in session or 'uid' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        uid = session['uid']
        db = get_db()
        
        if not data.get('full_name') or not data.get('roll_number'):
             return jsonify({'status': 'error', 'message': 'Missing required fields'}), 400

        student_ref = db.collection('organizations').document(uid).collection('students').document()
        student_ref.set(data)
        
        return jsonify({'status': 'success', 'id': student_ref.id})
    except Exception as e:
        print(f"Error adding student: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@api_bp.route('/api/add_bus', methods=['POST'])
def api_add_bus():
    if 'user' not in session or 'uid' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    try:
        data = request.get_json()
        uid = session['uid']
        db = get_db()
        bus_ref = db.collection('organizations').document(uid).collection('buses').document()
        bus_ref.set(data)
        return jsonify({'status': 'success', 'id': bus_ref.id})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@api_bp.route('/api/add_driver', methods=['POST'])
def api_add_driver():
    if 'user' not in session or 'uid' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    try:
        data = request.get_json()
        uid = session['uid']
        db = get_db()
        
        # Ensure required fields are present
        required_fields = ['full_name', 'license_number', 'phone_number']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'status': 'error', 'message': f'Missing required field: {field}'}), 400

        driver_data = {
            'full_name': data['full_name'],
            'license_number': data['license_number'],
            'phone_number': data['phone_number'],
            'assigned_bus': data.get('assigned_bus', ''),
            'date_of_birth': data.get('date_of_birth', ''),
            'joining_date': data.get('joining_date', ''),
            'license_expiry_date': data.get('license_expiry_date', ''),
            'emergency_contact_name': data.get('emergency_contact_name', ''),
            'emergency_contact_phone': data.get('emergency_contact_phone', ''),
            'blood_group': data.get('blood_group', ''),
            'address': data.get('address', '')
        }
        
        driver_ref = db.collection('organizations').document(uid).collection('drivers').document()
        driver_ref.set(driver_data)
        return jsonify({'status': 'success', 'id': driver_ref.id})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@api_bp.route('/api/add_route', methods=['POST'])
def api_add_route():
    if 'user' not in session or 'uid' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    try:
        data = request.get_json()
        uid = session['uid']
        db = get_db()
        route_ref = db.collection('organizations').document(uid).collection('routes').document()
        route_ref.set(data)
        return jsonify({'status': 'success', 'id': route_ref.id})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@api_bp.route('/api/update_bus/<bus_id>', methods=['POST'])
def api_update_bus(bus_id):
    if 'user' not in session or 'uid' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    try:
        data = request.get_json()
        uid = session['uid']
        db = get_db()
        bus_ref = db.collection('organizations').document(uid).collection('buses').document(bus_id)
        bus_ref.update(data)
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@api_bp.route('/api/update_driver/<driver_id>', methods=['POST'])
def api_update_driver(driver_id):
    if 'user' not in session or 'uid' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    try:
        data = request.get_json()
        uid = session['uid']
        db = get_db()
        driver_ref = db.collection('organizations').document(uid).collection('drivers').document(driver_id)
        driver_ref.update(data)
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@api_bp.route('/api/update_route/<route_id>', methods=['POST'])
def api_update_route(route_id):
    if 'user' not in session or 'uid' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    try:
        data = request.get_json()
        uid = session['uid']
        db = get_db()
        route_ref = db.collection('organizations').document(uid).collection('routes').document(route_id)
        route_ref.update(data)
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
