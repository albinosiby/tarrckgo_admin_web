from flask import Blueprint, request, session, jsonify
from app.services.firebase_service import get_db, get_bucket, get_db_rtdb
from firebase_admin import auth, firestore
import uuid
import time
from datetime import datetime

api_bp = Blueprint('api', __name__)

def upload_file(file, folder):
    if not file:
        return None
    try:
        bucket = get_bucket()
        filename = f"{folder}/{uuid.uuid4()}_{file.filename}"
        blob = bucket.blob(filename)
        blob.upload_from_file(file, content_type=file.content_type)
        blob.make_public()
        return blob.public_url
    except Exception as e:
        print(f"Error uploading file: {e}")
        return None

def create_firebase_user(phone_number, uid):
    try:
        phone_number = str(phone_number).replace(" ", "").replace("-", "")

        # Indian number handling
        if len(phone_number) == 11 and phone_number.startswith("0"):
            phone_number = phone_number[1:]

        if len(phone_number) == 10:
            phone_number = "+91" + phone_number

        if not phone_number.startswith("+"):
            return None, "Invalid phone number format"

        try:
            user = auth.create_user(
                uid=str(uid),        # 🔥 UID (Roll No or License No)
                phone_number=phone_number
            )
            print(f"Auth created for user {uid}")
            return user.uid, None

        except auth.UidAlreadyExistsError:
            # Student already exists in Auth
            user = auth.get_user(str(uid))
            return user.uid, None

    except Exception as e:
        return None, str(e)


@api_bp.route('/api/generate_student_id', methods=['GET'])
def api_generate_student_id():
    if 'user' not in session or 'uid' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    try:
        uid = session['uid']
        db = get_db()
        # Generate a new ID references
        ref = db.collection('organizations').document(uid).collection('students').document()
        return jsonify({'status': 'success', 'student_id': ref.id})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
@api_bp.route('/api/rfid/initiate', methods=['POST'])
def api_rfid_initiate():
    if 'uid' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401

    data = request.get_json()
    roll_number = data.get('roll_number')

    if not roll_number:
        return jsonify({'status': 'error', 'message': 'Roll number required'}), 400

    uid = session['uid']
    ref = get_db_rtdb().reference(f'organizations/{uid}/rfid_write')

    ref.set({
        'status': 'writing',
        'roll_number': roll_number,
        'student_id': roll_number,  # Add this to satisfy frontend check
        'timestamp': int(time.time() * 1000)
    })

    return jsonify({'status': 'success'})

@api_bp.route('/api/rfid/status', methods=['GET'])
def api_rfid_status():
    if 'user' not in session or 'uid' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    try:
        uid = session['uid']
        ref = get_db_rtdb().reference(f'organizations/{uid}/rfid_write')
        data = ref.get()
        
        if not data:
             return jsonify({'status': 'unknown'})
             
        return jsonify(data)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@api_bp.route('/api/add_student', methods=['POST'])
def api_add_student():
    if 'uid' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401

    data = request.form.to_dict() if not request.is_json else request.get_json()
    uid = session['uid']
    db = get_db()

    roll_number = str(data.get('roll_number', '')).strip()
    parent_phone = data.get('parent_phone')
    student_phone = data.get('student_phone')

    if not roll_number or not student_phone:
        return jsonify({'status': 'error', 'message': 'Roll number & student phone required'}), 400

    # 🔍 Check Organization Settings for Payment Rule
    org_ref = db.collection('organizations').document(uid)
    org_doc = org_ref.get()
    fee_details = ''
    if org_doc.exists:
        fee_details = org_doc.to_dict().get('feeDetails', '')

    # Rule: If Yearly payment, student cannot be assigned bus initially (due > 0)
    # Removing this check as bus assignment is no longer part of adding student
    
    # 🔐 Create Auth User (ROLL NUMBER AS UID)
    auth_uid, error = create_firebase_user(student_phone, roll_number)
    if not auth_uid:
        return jsonify({'status': 'error', 'message': error}), 400

    # Prevent overwrite
    student_ref = db.collection('organizations') \
        .document(uid) \
        .collection('students') \
        .document(roll_number)

    if student_ref.get().exists:
        return jsonify({'status': 'error', 'message': 'Student already exists'}), 400

    # 📷 Photo Upload
    profile_photo_url = None
    if 'student_photo' in request.files:
        file = request.files['student_photo']
        if file.filename:
            profile_photo_url = upload_file(file, f"students/{uid}")

    try:
        fee_amount = float(data.get('fee_amount', 0))
    except ValueError:
        fee_amount = 0

    # 🚌 Bus & Route Assignment Logic (Based on Stop)
    stop_id_input = data.get('bus_stop_id', '') # Assuming frontend sends this ID
    stop_name_input = data.get('bus_stop', '')

    bus_id_assigned = ''
    bus_number_assigned = ''
    route_id_assigned = ''
    route_name_assigned = ''

    if stop_id_input:
        # 1. Find the Route containing this Stop
        # Search all routes for this stop ID within their 'stops' array
        routes_ref = db.collection('organizations').document(uid).collection('routes')
        all_routes = routes_ref.stream()
        found_route = None
        
        for r_doc in all_routes:
            r_data = r_doc.to_dict()
            stops_list = r_data.get('stops', [])
            
            # Check if stop is in this route
            is_in_route = False
            if isinstance(stops_list, list):
                for s in stops_list:
                    if isinstance(s, dict) and s.get('id') == stop_id_input:
                        is_in_route = True
                        break
                    elif isinstance(s, str) and s == stop_name_input: # Fallback for legacy string match
                        is_in_route = True
                        break
            
            if is_in_route:
                found_route = r_data
                found_route['id'] = r_doc.id
                break
        
        if found_route:
            route_id_assigned = found_route.get('id')
            route_name_assigned = found_route.get('route_name')
            assigned_bus_id = found_route.get('assigned_bus')
            
            if assigned_bus_id:
                # 2. Get Bus Details
                bus_ref = db.collection('organizations').document(uid).collection('buses').document(assigned_bus_id)
                bus_doc = bus_ref.get()
                if bus_doc.exists:
                    b_data = bus_doc.to_dict()
                    bus_id_assigned = bus_doc.id
                    bus_number_assigned = b_data.get('bus_number', '')
                    
                    # Decrement available seats
                    bus_ref.update({'avail_seats': firestore.Increment(-1)}) 

        # 3. Update Stop Document with Student ID
        if stop_id_input:
            stop_ref = db.collection('organizations').document(uid).collection('stops').document(stop_id_input)
            if stop_ref.get().exists:
                stop_ref.update({
                    'assigned_students': firestore.ArrayUnion([roll_number]) # Using roll_number as student ID
                })

    student_data = {
        'full_name': data.get('full_name', ''),
        'roll_number': roll_number,
        'auth_uid': roll_number,           # 🔥 SAME
        'parent_name': data.get('parent_name', ''),
        'parent_phone': parent_phone,
        'student_phone': student_phone,
        'email': data.get('email', ''),
        'dob': data.get('dob', ''),
        'address': data.get('address', ''),
        'batch': data.get('batch', ''),
        'bus_id': bus_id_assigned,
        'bus_number': bus_number_assigned,
        'route_id': route_id_assigned or data.get('route_id', ''),
        'route_name': route_name_assigned or data.get('route_name', ''),
        'bus_stop': data.get('bus_stop', ''),
        'bus_stop_id': data.get('bus_stop_id', ''), # Store stop ID too for reference
        'payment_type': data.get('payment_type', ''),
        'fee_amount': fee_amount,
        'paid': 0,
        'due': fee_amount,
        'due': fee_amount,
        'can_travel': False, # Initialized to False as per request (unless fee is 0 potentially, but user said initially false)
        'created_at': firestore.SERVER_TIMESTAMP
    }

    if profile_photo_url:
        student_data['profile_photo_url'] = profile_photo_url

    student_ref.set(student_data)

    return jsonify({'status': 'success', 'student_id': roll_number})

@api_bp.route('/api/delete_student/<roll_number>', methods=['POST'])
def api_delete_student(roll_number):
    if 'uid' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401

    uid = session['uid']
    db = get_db()

    student_ref = db.collection('organizations') \
        .document(uid) \
        .collection('students') \
        .document(roll_number)

    # 1. Fetch student data to get auth_uid
    student_snap = student_ref.get()
    auth_uid = roll_number # Default fallback
    
    if student_snap.exists:
        student_data = student_snap.to_dict()
        auth_uid = student_data.get('auth_uid', roll_number)

        # Release Bus Seat
        bus_id = student_data.get('bus_id')
        if bus_id:
            bus_ref = db.collection('organizations').document(uid).collection('buses').document(bus_id)
            bus_snap = bus_ref.get()
            if bus_snap.exists:
                current_avail = int(bus_snap.to_dict().get('avail_seats', 0))
                bus_ref.update({'avail_seats': current_avail + 1})

    # 2. Delete Firestore Document
    student_ref.delete()

    # 3. Delete Auth user
    try:
        auth.delete_user(auth_uid)
        print(f"Auth deleted for uid: {auth_uid}")
    except Exception as e:
        print(f"Auth delete warning (uid: {auth_uid}): {e}")

    return jsonify({'status': 'success'})


@api_bp.route('/api/add_driver', methods=['POST'])
def api_add_driver():
    if 'user' not in session or 'uid' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    try:
        # Handle both JSON and Form Data
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form.to_dict()
            
        uid = session['uid']
        db = get_db()
        
        # Ensure required fields are present
        required_fields = ['full_name', 'license_number', 'phone_number']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'status': 'error', 'message': f'Missing required field: {field}'}), 400

        # VALIDATION: Check Bus Assignment BEFORE creating user
        bus_ref = None
        if data.get('assigned_bus'):
            bus_ref = db.collection('organizations').document(uid).collection('buses').document(data['assigned_bus'])
            bus_snap = bus_ref.get()
            if bus_snap.exists:
                b_data = bus_snap.to_dict()
                if b_data.get('driver_id'):
                     return jsonify({'status': 'error', 'message': f"Bus {b_data.get('bus_number')} is already assigned to another driver."}), 400

        # 1. Create Auth User FIRST
        driver_uid = None
        if data.get('phone_number'):
            # Use License Number as UID
            driver_uid, auth_error = create_firebase_user(data['phone_number'], data['license_number'])
            if not driver_uid:
                return jsonify({'status': 'error', 'message': f'Failed to create Login ID: {auth_error}'}), 400
        else:
             return jsonify({'status': 'error', 'message': 'Phone number is required for driver login creation'}), 400

        # Handle Driver Photo Upload
        profile_photo_url = None
        if 'driver_photo' in request.files:
            file = request.files['driver_photo']
            if file.filename:
                profile_photo_url = upload_file(file, f"drivers/{uid}")

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
            'driver_uid': driver_uid, # explicit field
            'can_add_stop': str(data.get('can_add_stop', 'false')).lower() == 'true'
        }
        
        if profile_photo_url:
            driver_data['profile_photo_url'] = profile_photo_url
        
        # 2. Use Auth UID as Document ID
        driver_ref = db.collection('organizations').document(uid).collection('drivers').document(driver_uid)
        
        if driver_ref.get().exists:
            return jsonify({'status': 'error', 'message': 'Driver with this License Number already exists'}), 400

        driver_ref.set(driver_data)
        
        # If assigned_bus is present, update the Bus document
        if bus_ref:
            bus_ref.update({
                'driver_id': driver_uid,
                'driver_name': data['full_name']
            })

        return jsonify({'status': 'success', 'id': driver_ref.id, 'driver_uid': driver_uid})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@api_bp.route('/api/add_bus', methods=['POST'])
def api_add_bus():
    if 'user' not in session or 'uid' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    try:
        data = request.get_json()
        uid = session['uid']
        db = get_db()
        
        # Check if registration number already exists
        reg_no = data.get('registration_no')
        if reg_no:
            buses_ref = db.collection('organizations').document(uid).collection('buses')
            query = buses_ref.where('registration_no', '==', reg_no).get()
            if len(query) > 0:
                 return jsonify({'status': 'error', 'message': 'Bus with this Registration Number already exists'}), 400
        
        bus_ref = db.collection('organizations').document(uid).collection('buses').document()
        
        # Handle driver assignment
        driver_id = data.get('driver_id')
        if driver_id:
            driver_ref = db.collection('organizations').document(uid).collection('drivers').document(driver_id)
            driver_data = driver_ref.get().to_dict()
            if driver_data.get('assigned_bus'):
                return jsonify({'status': 'error', 'message': f"Driver {driver_data.get('full_name')} is already assigned to a bus."}), 400
            
            # Link driver to bus
            data['driver_name'] = driver_data.get('full_name')
            driver_ref.update({'assigned_bus': bus_ref.id})

        # Handle route assignment
        route_id = data.get('route_id')
        if route_id:
            route_ref = db.collection('organizations').document(uid).collection('routes').document(route_id)
            route_ref.update({'assigned_bus': bus_ref.id})

        # Set available seats equal to capacity initially
        try:
            capacity = int(data.get('capacity', 0))
            data['avail_seats'] = capacity
        except ValueError:
            data['avail_seats'] = 0

        bus_ref.set(data)

        # 🚀 Initialize Realtime Database for RFID
        try:
            rtdb_ref = get_db_rtdb().reference(f'organizations/{uid}/rfid_read/{bus_ref.id}')
            rtdb_ref.set({
                '_init': 1,
                'bus_number': data.get('bus_number', ''),
                'created_at': int(time.time() * 1000),
                'recent_scan': {
                    'cardid': "VML22CS036",
                    'lastscan': datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
                    'status': "initialized",
                    'time': datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                }
            })
            
            # 🚀 Initialize Realtime Database for Location
            loc_ref = get_db_rtdb().reference(f'organizations/{uid}/bus_location/{bus_ref.id}')
            loc_ref.set({
                'latitude': 0.0,
                'longitude': 0.0,
                'bus_number': data.get('bus_number', ''),
                'speed': 0,
                'heading': 0,
                'timestamp': int(time.time() * 1000)
            })
            
        except Exception as rtdb_e:
            print(f"RTDB Init Warning: {rtdb_e}")
            # Continue even if RTDB init fails, as the main bus is created.

        return jsonify({'status': 'success', 'id': bus_ref.id})
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
                    
                    # VALIDATION: Check if new driver is already assigned
                    nd_snap = new_driver_ref.get()
                    if nd_snap.exists:
                        nd_data = nd_snap.to_dict()
                        if nd_data.get('assigned_bus'):
                             return jsonify({'status': 'error', 'message': f"Driver {nd_data.get('full_name')} is already assigned to bus {nd_data.get('assigned_bus')}."}), 400
                    
                    new_driver_ref.update({'assigned_bus': bus_id})

        # Handle route change if route_id is provided
        # We check keys 'route_id' specifically to know if it's being updated
        if 'route_id' in data:
            new_route_id = data['route_id']
            
            # Get current bus data to find old route
            # Note: We might have already fetched current_bus above, but to be safe/clean re-fetch or use variable if scope allows.
            # Ideally store current_bus at start of try block if used multiple times.
            # For now, just re-fetch or assume 'current_bus' variable from driver block is accessible if defined.
            # But driver block only runs if 'driver_id' in data. 
            # So lets fetch safely.
            current_bus_snap = bus_ref.get()
            current_bus_data = current_bus_snap.to_dict()
            old_route_id = current_bus_data.get('route_id')
            
            if old_route_id != new_route_id:
                # Unassign from old route if exists
                if old_route_id:
                     old_route_ref = db.collection('organizations').document(uid).collection('routes').document(old_route_id)
                     old_route_ref.update({'assigned_bus': ''})
                
                # Assign to new route if exists
                if new_route_id:
                    new_route_ref = db.collection('organizations').document(uid).collection('routes').document(new_route_id)
                    new_route_ref.update({'assigned_bus': bus_id})

                    # UPDATE STUDENTS associated with this route
                    try:
                        students_ref = db.collection('organizations').document(uid).collection('students')
                        
                        # Set to collect all unique student IDs to update
                        student_ids_to_update = set()
                        
                        # 1. Get Route Data to find Stops
                        route_doc = new_route_ref.get()
                        if route_doc.exists:
                            r_data = route_doc.to_dict()
                            stops_list = r_data.get('stops', [])
                            
                            # Find students with this route_id
                            students_by_route = students_ref.where('route_id', '==', new_route_id).stream()
                            for s in students_by_route:
                                student_ids_to_update.add(s.id)

                            # Find students by Stop Name/ID if route_id is missing
                            # Iterate through stops and query students
                            for stop in stops_list:
                                stop_val = stop.get('id') if isinstance(stop, dict) else stop
                                if stop_val:
                                    # Query by bus_stop_id (if using IDs) or bus_stop (if using names)
                                    # We check both fields to be safe
                                    if isinstance(stop_val, str): # Verify valid ID string
                                        # Strategy: Query generic 'bus_stop' field which might hold Name or ID
                                        # Or better, query specific fields if schema is strict.
                                        # Assuming 'bus_stop_id' stores ID and 'bus_stop' stores Name.
                                        
                                        # Query by ID
                                        st_by_id = students_ref.where('bus_stop_id', '==', stop_val).stream()
                                        for s in st_by_id: student_ids_to_update.add(s.id)
                                        
                                        # If stop is a dict with 'stop_name', query by name too
                                        if isinstance(stop, dict) and 'stop_name' in stop:
                                            st_by_name = students_ref.where('bus_stop', '==', stop['stop_name']).stream()
                                            for s in st_by_name: student_ids_to_update.add(s.id)
                        
                        bus_number = data.get('bus_number', current_bus_data.get('bus_number'))
                        
                        batch = db.batch()
                        batch_count = 0
                        
                        for sid in student_ids_to_update:
                            s_ref = students_ref.document(sid)
                            batch.update(s_ref, {
                                'bus_id': bus_id,
                                'bus_number': bus_number,
                                'route_id': new_route_id, # Ensure route_id is synced
                                'route_name': r_data.get('route_name', '') # Ensure route name is synced
                            })
                            batch_count += 1
                            if batch_count >= 450:
                                batch.commit()
                                batch = db.batch()
                                batch_count = 0
                        
                        if batch_count > 0:
                            batch.commit()
                        
                        # RECALCULATE AVAILABLE SEATS
                        # Count total students assigned to this bus
                        total_assigned_snaps = students_ref.where('bus_id', '==', bus_id).stream()
                        total_assigned_count = sum(1 for _ in total_assigned_snaps)
                        
                        # Get capacity (from incoming data or existing)
                        capacity_val = int(data.get('capacity', current_bus_data.get('capacity', 0)))
                        new_avail_seats = max(0, capacity_val - total_assigned_count)
                        
                        # Update bus avail_seats immediately
                        bus_ref.update({'avail_seats': new_avail_seats})
                            
                    except Exception as e:
                        print(f"Error syncing students for bus {bus_id}: {e}")

        bus_ref.update(data)
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@api_bp.route('/api/update_driver/<driver_id>', methods=['POST'])
def api_update_driver(driver_id):
    if 'user' not in session or 'uid' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    try:
        # Handle both JSON and Form Data
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form.to_dict()
            
        uid = session['uid']
        db = get_db()
        driver_ref = db.collection('organizations').document(uid).collection('drivers').document(driver_id)
        
        # Handle Photo Upload
        profile_photo_url = None
        if 'driver_photo' in request.files:
            file = request.files['driver_photo']
            if file.filename:
                profile_photo_url = upload_file(file, f"drivers/{uid}")
        
        if profile_photo_url:
            driver_data['profile_photo_url'] = profile_photo_url
        
        # Handle assigned_bus change
        if 'assigned_bus' in data:
             new_bus_id = data['assigned_bus']
             
             # Get current driver data to find old assigned bus
             current_driver = driver_ref.get().to_dict()
             old_bus_id = current_driver.get('assigned_bus')
             
             if old_bus_id != new_bus_id:
                 # Unassign from old bus if exists
                 if old_bus_id:
                     old_bus_ref = db.collection('organizations').document(uid).collection('buses').document(old_bus_id)
                     old_bus_ref.update({
                         'driver_id': '',
                         'driver_name': ''
                     })
                 
                 # Assign to new bus if exists
                 if new_bus_id:
                     new_bus_ref = db.collection('organizations').document(uid).collection('buses').document(new_bus_id)
                     
                     # VALIDATION: Check if bus is already assigned
                     nb_snap = new_bus_ref.get()
                     if nb_snap.exists:
                         nb_data = nb_snap.to_dict()
                         if nb_data.get('driver_id'):
                              return jsonify({'status': 'error', 'message': f"Bus {nb_data.get('bus_number')} is already assigned to driver {nb_data.get('driver_name')}."}), 400
                     
                     # Get driver name (check payload or current_driver)
                     driver_name = data.get('full_name', current_driver.get('full_name', ''))
                     new_bus_ref.update({
                         'driver_id': driver_id,
                         'driver_name': driver_name
                     })

        # Prepare update data, excluding special fields handled above
        update_data = {k: v for k, v in data.items() if k not in ['driver_photo', 'assigned_bus']}
        
        # Handle boolean field specifically
        if 'can_add_stop' in data:
             update_data['can_add_stop'] = str(data.get('can_add_stop', 'false')).lower() == 'true'

        driver_ref.update(update_data)
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
        
        # Handle assigned_bus change
        if 'assigned_bus' in data:
            new_bus_id = data['assigned_bus']
            
            # Fetch current route data to find old bus
            current_route_snap = route_ref.get()
            if current_route_snap.exists:
                current_route = current_route_snap.to_dict()
                old_bus_id = current_route.get('assigned_bus')
                
                # If bus changed
                if old_bus_id != new_bus_id:
                    # 1. Unassign from old bus if exists
                    if old_bus_id:
                        old_bus_ref = db.collection('organizations').document(uid).collection('buses').document(old_bus_id)
                        old_bus_ref.update({
                            'route': 'N/A',
                            'route_id': ''
                        })
                    
                    # 2. Assign to new bus if exists
                    if new_bus_id:
                        new_bus_ref = db.collection('organizations').document(uid).collection('buses').document(new_bus_id)
                        
                        # Get route name (from payload if updating, else current)
                        route_name = data.get('route_name', current_route.get('route_name', ''))
                        
                        # Update new bus
                        new_bus_ref.update({
                            'route': route_name,
                            'route_id': route_id
                        })

        route_ref.update(data)
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@api_bp.route('/api/add_payment/<student_id>', methods=['POST'])
def api_add_payment(student_id):
    if 'user' not in session or 'uid' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    try:
        data = request.get_json()
        uid = session['uid']
        db = get_db()
        
        # Validate data
        if not data.get('amount') or not data.get('date'):
             return jsonify({'status': 'error', 'message': 'Missing required fields'}), 400

        # Add payment to subcollection
        student_doc_ref = db.collection('organizations').document(uid).collection('students').document(student_id)
        payment_ref = student_doc_ref.collection('payments').document()
        payment_ref.set(data)
        
        # Update student document totals (paid and due)
        student_data = student_doc_ref.get().to_dict()
        if student_data:
             current_paid = float(student_data.get('paid', 0))
             fee_amount = float(student_data.get('fee_amount', 0))
             new_payment = float(data.get('amount', 0))
             
             new_paid = current_paid + new_payment
             new_due = fee_amount - new_paid
             
             updates = {
                 'paid': new_paid,
                 'due': new_due
             }
             if new_due <= 0:
                 updates['can_travel'] = True
             
             student_doc_ref.update(updates)
        
        return jsonify({'status': 'success', 'id': payment_ref.id})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
        
@api_bp.route('/api/update_student/<roll_number>', methods=['POST'])
def api_update_student(roll_number):
    if 'uid' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401

    uid = session['uid']
    db = get_db()
    data = request.form.to_dict() if not request.is_json else request.get_json()

    # 🔍 Fetch Current Student Data for Comparison
    student_curr_ref = db.collection('organizations').document(uid).collection('students').document(roll_number)
    student_curr_snap = student_curr_ref.get()
    
    if not student_curr_snap.exists:
        return jsonify({'status': 'error', 'message': 'Student not found'}), 404

    student_curr = student_curr_snap.to_dict()
    
    # 🚏 Stop-Based Assignment & Stop Record Update Logic
    # Check if stop is being changed (present in data)
    if 'bus_stop_id' in data:
        new_stop_id = data.get('bus_stop_id')
        old_stop_id = student_curr.get('bus_stop_id')
        
        # Determine effective new IDs (default to remove if not found)
        derived_bus_id = ''
        derived_bus_number = ''
        derived_route_id = ''
        derived_route_name = ''
        
        if new_stop_id:
             # 1. Find the Route containing this Stop
            routes_ref = db.collection('organizations').document(uid).collection('routes')
            all_routes = routes_ref.stream()
            found_route = None
            
            # Simple retrieval if stop_id provided
            for r_doc in all_routes:
                r_data = r_doc.to_dict()
                stops_list = r_data.get('stops', [])
                for s in stops_list:
                    if (isinstance(s, dict) and s.get('id') == new_stop_id) or (isinstance(s, str) and s == data.get('bus_stop')):
                        found_route = r_data
                        found_route['id'] = r_doc.id
                        break
                if found_route: break
            
            if found_route:
                derived_route_id = found_route.get('id')
                derived_route_name = found_route.get('route_name')
                assigned_bus_id = found_route.get('assigned_bus')
                
                if assigned_bus_id:
                     bus_ref = db.collection('organizations').document(uid).collection('buses').document(assigned_bus_id)
                     bus_doc = bus_ref.get()
                     if bus_doc.exists:
                         derived_bus_id = bus_doc.id
                         derived_bus_number = bus_doc.to_dict().get('bus_number', '')

        # Update data with derived values
        data['bus_id'] = derived_bus_id
        data['bus_number'] = derived_bus_number
        data['route_id'] = derived_route_id
        data['route_name'] = derived_route_name

        # 2. Update Stop Records (Assigned Students)
        # Remove from old stop (strictly using ID)
        if old_stop_id and old_stop_id != new_stop_id:
             old_stop_ref = db.collection('organizations').document(uid).collection('stops').document(old_stop_id)
             if old_stop_ref.get().exists:
                 old_stop_ref.update({
                     'assigned_students': firestore.ArrayRemove([roll_number])
                 })
        
        # Add to new stop
        if new_stop_id and new_stop_id != old_stop_id:
             new_stop_ref = db.collection('organizations').document(uid).collection('stops').document(new_stop_id)
             if new_stop_ref.get().exists:
                 new_stop_ref.update({
                     'assigned_students': firestore.ArrayUnion([roll_number])
                 })

    # 🚍 Bus Assignment & Capacity Logic (Existing refined)
    # Check if bus_id is in data (updated above or passed)
    if 'bus_id' in data:
        new_bus_id = data.get('bus_id')
        old_bus_id = student_curr.get('bus_id')
        
        if new_bus_id != old_bus_id:
            # A. Assigning to a New Bus (New ID is present)
            if new_bus_id:
                try:
                    bus_new_ref = db.collection('organizations').document(uid).collection('buses').document(new_bus_id)
                    # Atomic decrement. Will fail if doc doesn't exist.
                    bus_new_ref.update({'avail_seats': firestore.Increment(-1)})
                except Exception as e:
                    print(f"Warning: Failed to decrement seats for bus {new_bus_id}: {e}")

            # B. Removing from Old Bus (Old ID was present)
            if old_bus_id:
                try:
                    bus_old_ref = db.collection('organizations').document(uid).collection('buses').document(old_bus_id)
                    bus_old_ref.update({'avail_seats': firestore.Increment(1)})
                except Exception as e:
                    print(f"Warning: Failed to increment seats for bus {old_bus_id}: {e}")

    # 🚫 Never allow roll number change
    data.pop('roll_number', None)

    # Photo update
    if 'student_photo' in request.files:
        file = request.files['student_photo']
        if file.filename:
            data['profile_photo_url'] = upload_file(file, f"students/{uid}")

    student_curr_ref.update(data)
    return jsonify({'status': 'success'})

@api_bp.route('/api/delete_driver/<driver_id>', methods=['POST'])
def api_delete_driver(driver_id):
    if 'user' not in session or 'uid' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    try:
        uid = session['uid']
        db = get_db()
        driver_ref = db.collection('organizations').document(uid).collection('drivers').document(driver_id)
        
        # Get driver data to find assigned bus and clean up
        driver_snap = driver_ref.get()
        if not driver_snap.exists:
             return jsonify({'status': 'error', 'message': 'Driver not found'}), 404
        
        driver_data = driver_snap.to_dict()
        
        # Unassign from Bus if assigned
        assigned_bus_id = driver_data.get('assigned_bus')
        if assigned_bus_id:
             bus_ref = db.collection('organizations').document(uid).collection('buses').document(assigned_bus_id)
             bus_ref.update({
                 'driver_id': '',
                 'driver_name': ''
             })

        # Delete from Firestore
        driver_ref.delete()
        
        # Delete from Firebase Auth
        try:
            auth.delete_user(driver_id)
            print(f"Successfully deleted auth user: {driver_id}")
        except Exception as auth_e:
            print(f"Error deleting auth user (might not exist or other error): {auth_e}")
            # We continue even if auth delete fails, as the main record is gone.
            
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@api_bp.route('/api/live_trips', methods=['GET'])
def api_live_trips():
    if 'user' not in session or 'uid' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    try:
        uid = session['uid']
        db = get_db()
        org_ref = db.collection('organizations').document(uid)
        
        # Fetch Routes for mapping (could be optimized by cache or minimal fields)
        routes_ref = org_ref.collection('routes')
        route_map = {}
        for r in routes_ref.stream():
            rd = r.to_dict()
            route_map[r.id] = rd.get('route_name', 'Unknown Route')

        buses_ref = org_ref.collection('buses')
        buses_data = []
        
        for b in buses_ref.stream():
            bus = b.to_dict()
            bus_id = b.id
            
            # Map route name
            r_id = bus.get('route_id')
            route_name = route_map.get(r_id, 'No Route Assigned') if r_id else 'No Route Assigned'
            
            buses_data.append({
                'id': bus_id,
                'bus_number': bus.get('bus_number', ''),
                'registration_no': bus.get('registration_no', ''),
                'route_name': route_name,
                'trip_status': bus.get('trip_status', 'Not Started'),
                'on_board_count': bus.get('on_board_count', 0),
                'capacity': bus.get('capacity', '-')
            })
            
        return jsonify({'status': 'success', 'buses': buses_data})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@api_bp.route('/api/fix_bus_seats', methods=['GET'])
def api_fix_bus_seats():
    if 'user' not in session or 'uid' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    try:
        uid = session['uid']
        db = get_db()
        
        # 1. Get all buses
        buses_ref = db.collection('organizations').document(uid).collection('buses')
        buses = buses_ref.stream()
        
        updated_count = 0
        details = []
        
        for doc in buses:
            data = doc.to_dict()
            capacity = int(data.get('capacity', 0))
            # If avail_seats is missing or 0 (and capacity > 0), reset it.
            # You might want more complex logic (e.g. check actual students), 
            # but for a quick fix, resetting to capacity (assuming empty) is a start.
            if 'avail_seats' not in data:
                 doc.reference.update({'avail_seats': capacity})
                 updated_count += 1
        
        return jsonify({'status': 'success', 'updated': updated_count})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@api_bp.route('/api/add_stop', methods=['POST'])
def api_add_stop():
    if 'uid' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    try:
        data = request.get_json()
        uid = session['uid']
        db = get_db()
        
        # Basic Validation
        if not data.get('stop_name'):
             return jsonify({'status': 'error', 'message': 'Stop Name is required'}), 400

        stop_ref = db.collection('organizations').document(uid).collection('stops').document()
        
        stop_data = {
            'stop_name': data.get('stop_name'),
            'lat': float(data.get('lat', 0.0)),
            'long': float(data.get('long', 0.0)),
            'fee': float(data.get('fee', 0)),
            'created_at': firestore.SERVER_TIMESTAMP
        }
        
        stop_ref.set(stop_data)
        return jsonify({'status': 'success', 'id': stop_ref.id})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@api_bp.route('/api/update_stop/<stop_id>', methods=['POST'])
def api_update_stop(stop_id):
    if 'uid' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    try:
        data = request.get_json()
        uid = session['uid']
        db = get_db()
        stop_ref = db.collection('organizations').document(uid).collection('stops').document(stop_id)
        
        updates = {}
        if 'stop_name' in data: updates['stop_name'] = data['stop_name']
        if 'lat' in data: updates['lat'] = float(data['lat'])
        if 'long' in data: updates['long'] = float(data['long'])
        if 'fee' in data: updates['fee'] = float(data['fee'])
        
        stop_ref.update(updates)
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@api_bp.route('/api/delete_stop/<stop_id>', methods=['POST'])
def api_delete_stop(stop_id):
    if 'uid' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    try:
        uid = session['uid']
        db = get_db()
        stop_ref = db.collection('organizations').document(uid).collection('stops').document(stop_id)
        stop_ref.delete()
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

        for bus in buses:
            bus_data = bus.to_dict()
            bus_id = bus.id
            
            # Get Capacity (handle string/int/missing)
            try:
                capacity = int(bus_data.get('capacity', 0))
            except ValueError:
                capacity = 0
            
            # 2. Count current students assigned to this bus
            students_ref = db.collection('organizations').document(uid).collection('students')
            # Firestore count query is efficient
            count_query = students_ref.where('bus_id', '==', bus_id).count()
            count_results = count_query.get()
            current_on_board_count = count_results[0][0].value
            
            # 3. Calculate Available Seats
            avail_seats = capacity - current_on_board_count
            
            # Update Bus
            bus.reference.update({
                'avail_seats': avail_seats,
                'on_board_count': current_on_board_count # Optional: Sync this too if needed, but mainly avail_seats
            })
            
            updated_count += 1
            details.append(f"Bus {bus_data.get('bus_number')} ({bus_id}): Cap={capacity}, Alloc={current_on_board_count}, Avail={avail_seats}")

        return jsonify({
            'status': 'success', 
            'message': f'Updated {updated_count} buses',
            'details': details
        })

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@api_bp.route('/api/reset_fee_status/<student_id>', methods=['POST'])
def api_reset_fee_status(student_id):
    if 'user' not in session or 'uid' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    try:
        uid = session['uid']
        db = get_db()
        
        student_ref = db.collection('organizations').document(uid).collection('students').document(student_id)
        student_snap = student_ref.get()
        
        if not student_snap.exists:
             return jsonify({'status': 'error', 'message': 'Student not found'}), 404
             
        student_data = student_snap.to_dict()
        fee_amount = float(student_data.get('fee_amount', 0))
        
        # Reset Logic
        student_ref.update({
            'paid': 0,
            'due': fee_amount,
            'can_travel': False
        })
        
        return jsonify({'status': 'success', 'message': 'Fee status reset for new academic year.'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
@api_bp.route('/api/reset_all_fees', methods=['POST'])
def api_reset_all_fees():
    if 'user' not in session or 'uid' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    try:
        uid = session['uid']
        db = get_db()
        
        # 1. Build a Fee Lookup Map: RouteName -> StopName -> Fee
        routes_ref = db.collection('organizations').document(uid).collection('routes')
        fee_map = {} # {'Route A': {'Stop 1': 5000, 'Stop 2': 6000}}
        
        for r_doc in routes_ref.stream():
            r_data = r_doc.to_dict()
            r_name = r_data.get('route_name')
            if r_name:
                stops = r_data.get('stops', [])
                # stops is a list of dicts: [{'name': 'Stop1', 'fee': '5000'}, ...]
                stop_fees = {}
                for s in stops:
                    s_name = s.get('name')
                    s_fee = s.get('fee', 0)
                    try:
                        stop_fees[s_name] = float(s_fee)
                    except:
                        stop_fees[s_name] = 0.0
                fee_map[r_name] = stop_fees
        
        # 2. Iterate Students and Reset
        students_ref = db.collection('organizations').document(uid).collection('students')
        students = students_ref.stream()
        
        count = 0
        batch = db.batch()
        batch_count = 0
        
        today_str = datetime.now().strftime('%Y-%m-%d')
        
        for student in students:
            student_data = student.to_dict()
            
            # Lookup current fee
            route_name = student_data.get('route_name')
            bus_stop = student_data.get('bus_stop')
            current_fee = float(student_data.get('fee_amount', 0)) # Default to existing
            
            if route_name in fee_map and bus_stop in fee_map[route_name]:
                current_fee = fee_map[route_name][bus_stop]
            
            batch.update(student.reference, {
                'paid': 0,
                'due': current_fee,     # Reset due to the CURRENT fee amount
                'fee_amount': current_fee, # Update fee amount in case it changed
                'can_travel': False,
                'last_fee_reset_date': today_str
            })
            
            batch_count += 1
            
            # Archive existing payments
            payments_ref = student.reference.collection('payments')
            # Only fetch non-archived ones ideally, or just all
            for p_doc in payments_ref.stream():
                batch.update(p_doc.reference, {'archived': True})
                batch_count += 1
                
                if batch_count >= 400:
                    batch.commit()
                    batch = db.batch()
                    batch_count = 0
            
            count += 1
            
            # Check batch limit
            if batch_count >= 400:
                batch.commit()
                batch = db.batch()
                batch_count = 0
        
        # Commit remaining
        if batch_count > 0:
            batch.commit()
            
        return jsonify({'status': 'success', 'message': f'Fee cycle reset for {count} students. History preserved (archived).'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
