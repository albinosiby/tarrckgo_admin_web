from flask import Blueprint, request, session, jsonify
from app.services.firebase_service import get_db
from firebase_admin import auth

api_bp = Blueprint('api', __name__)

def create_firebase_user(phone_number):
    try:
        # Cleanup phone number: remove spaces, dashes
        phone_number = str(phone_number).replace(' ', '').replace('-', '')
        
        # Basic formatting:
        # If 11 digits and starts with '0', remove the leading '0'
        if len(phone_number) == 11 and phone_number.startswith('0') and phone_number.isdigit():
            phone_number = phone_number[1:]

        # If 10 digits and probably Indian, prepend +91
        if len(phone_number) == 10 and phone_number.isdigit():
            phone_number = "+91" + phone_number
            
        # Ensure it starts with +
        if not phone_number.startswith('+'):
            msg = f"Invalid phone format: {phone_number}. Must be E.164 (e.g., +919999999999)"
            print(msg)
            return None, msg

        try:
            user = auth.create_user(phone_number=phone_number)
            print(f"Successfully created user: {user.uid} for phone {phone_number}")
            return user.uid, None
        except auth.PhoneNumberAlreadyExistsError:
            print(f"User with phone number {phone_number} already exists.")
            # Optionally fetch the existing user if needed, but for now just proceed
            try:
                user = auth.get_user_by_phone_number(phone_number)
                print(f"Retrieved existing user: {user.uid}")
                return user.uid, None
            except Exception as e:
                msg = f"Error retrieving existing user: {str(e)}"
                print(msg)
                return None, msg
    except Exception as e:
        msg = f"Error creating auth user: {str(e)}"
        print(msg)
        return None, msg

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
        
        # Create Auth User for Parent
        # Create Auth User for Parent
        if data.get('parent_phone'):
            parent_uid, error_msg = create_firebase_user(data['parent_phone'])
            if parent_uid:
                student_ref.update({'parent_uid': parent_uid})
            elif error_msg:
                 print(f"Warning adding student auth: {error_msg}")

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
        
        # Add driver_id to bus data if present
        if data.get('driver_id'):
            # Update driver's assigned_bus
            driver_ref = db.collection('organizations').document(uid).collection('drivers').document(data['driver_id'])
            driver_ref.update({'assigned_bus': bus_ref.id})

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

        # 1. Create Auth User FIRST
        driver_uid = None
        if data.get('phone_number'):
            driver_uid, auth_error = create_firebase_user(data['phone_number'])
            if not driver_uid:
                # Critical failure: Do not create driver in DB if Auth fails
                return jsonify({'status': 'error', 'message': f'Failed to create Login ID: {auth_error}'}), 400
        else:
             return jsonify({'status': 'error', 'message': 'Phone number is required for driver login creation'}), 400

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
            'address': data.get('address', ''),
            'driver_uid': driver_uid # explicit field
        }
        
        # 2. Use Auth UID as Document ID
        driver_ref = db.collection('organizations').document(uid).collection('drivers').document(driver_uid)
        driver_ref.set(driver_data)
        
        return jsonify({'status': 'success', 'id': driver_ref.id, 'driver_uid': driver_uid})
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
        
        # Handle driver change if driver_id is provided
        if 'driver_id' in data:
            new_driver_id = data['driver_id']
            
            # Get current bus data to find old driver
            current_bus = bus_ref.get().to_dict()
            old_driver_id = current_bus.get('driver_id')
            
            # If driver changed
            if old_driver_id != new_driver_id:
                # Unassign from old driver if exists
                if old_driver_id:
                     old_driver_ref = db.collection('organizations').document(uid).collection('drivers').document(old_driver_id)
                     old_driver_ref.update({'assigned_bus': ''})
                
                # Assign to new driver if exists
                if new_driver_id:
                    new_driver_ref = db.collection('organizations').document(uid).collection('drivers').document(new_driver_id)
                    new_driver_ref.update({'assigned_bus': bus_id})

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
