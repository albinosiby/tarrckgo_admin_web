from flask import Blueprint, render_template, session, redirect, url_for, request
from app.services.firebase_service import get_db

students_bp = Blueprint('students', __name__)

@students_bp.route('/students')
def students():
    if 'user' not in session: return redirect(url_for('auth.login'))
    uid = session.get('uid')
    db = get_db()
    
    # Get Filter Params
    search_query = request.args.get('q', '').lower()
    assignment_filter = request.args.get('assignment', '')
    bus_filter = request.args.get('bus', '')
    route_filter = request.args.get('route', '')

    # Fetch all students (Filter in memory for flexibility)
    students_ref = db.collection('organizations').document(uid).collection('students')
    all_students = []
    for doc in students_ref.stream():
        student = doc.to_dict()
        student['id'] = doc.id
        all_students.append(student)

    # Apply Filters
    filtered_students = []
    for s in all_students:
        # Search (Name or Roll Number)
        if search_query:
            full_name = s.get('full_name', '').lower()
            roll = s.get('roll_number', '').lower()
            if search_query not in full_name and search_query not in roll:
                continue
        
        # Assignment Filter
        if assignment_filter == 'assigned':
            if not s.get('bus_number'): continue
        elif assignment_filter == 'unassigned':
            if s.get('bus_number'): continue
            
        # Bus Filter
        if bus_filter:
            if s.get('bus_number') != bus_filter: continue
            
        # Route Filter
        if route_filter:
            # Route logic is a bit complex as it might be 'route_name' or derived from bus
            # Basic check on stored route_name
            if s.get('route_name') != route_filter: continue

        filtered_students.append(s)

    # Fetch Buses and Routes for Filter Dropdowns
    buses_ref = db.collection('organizations').document(uid).collection('buses')
    buses = [d.to_dict() for d in buses_ref.stream()]
    buses.sort(key=lambda x: x.get('bus_number', ''))

    routes_ref = db.collection('organizations').document(uid).collection('routes')
    routes = [d.to_dict() for d in routes_ref.stream()]
    routes.sort(key=lambda x: x.get('route_name', ''))

    return render_template('students.html', 
                           students=filtered_students, 
                           buses=buses, 
                           routes=routes,
                           filters={
                               'q': request.args.get('q', ''),
                               'assignment': assignment_filter,
                               'bus': bus_filter,
                               'route': route_filter
                           })

@students_bp.route('/add_student')
def add_student():
    if 'user' not in session: return redirect(url_for('auth.login'))
    uid = session.get('uid')
    db = get_db()
    
    # Fetch buses
    buses_ref = db.collection('organizations').document(uid).collection('buses')
    buses = []
    for doc in buses_ref.stream():
        b_data = doc.to_dict()
        b_data['id'] = doc.id
        buses.append(b_data)

    # Fetch routes
    routes_ref = db.collection('organizations').document(uid).collection('routes')
    routes = []
    for doc in routes_ref.stream():
        r_data = doc.to_dict()
        r_data['id'] = doc.id
        routes.append(r_data)

    # Fetch Organization Settings
    org_ref = db.collection('organizations').document(uid)
    org_doc = org_ref.get()
    payment_type = 'Monthly' # Default
    if org_doc.exists:
        org_data = org_doc.to_dict()
        payment_type = org_data.get('feeDetails', 'Monthly')

    return render_template('add_student.html', buses=buses, routes=routes, payment_type=payment_type)

@students_bp.route('/student_details/<student_id>')
def student_details(student_id):
    if 'user' not in session: return redirect(url_for('auth.login'))
    uid = session.get('uid')
    db = get_db()
    student_ref = db.collection('organizations').document(uid).collection('students').document(student_id)
    student = student_ref.get().to_dict()
    if student:
        student['id'] = student_id

        # Fetch buses
        buses_ref = db.collection('organizations').document(uid).collection('buses')
        buses = []
        bus_route_map = {}
        for doc in buses_ref.stream():
            b_data = doc.to_dict()
            b_data['id'] = doc.id
            buses.append(b_data)
            bus_route_map[doc.id] = b_data.get('route', '') # Map ID to Route Name
        
        # Fallback: If student doesn't have route_name, try to get it from assigned bus
        if not student.get('route_name'):
             bus_id = student.get('bus_id')
             if bus_id and bus_id in bus_route_map:
                 student['route_name'] = bus_route_map[bus_id]

        # Fetch routes
        routes_ref = db.collection('organizations').document(uid).collection('routes')
        routes = []
        for doc in routes_ref.stream():
            r_data = doc.to_dict()
            r_data['id'] = doc.id
            routes.append(r_data)
        
        # Fetch payments
        payments_ref = student_ref.collection('payments')
        payments = []
        total_paid = 0
        
        for doc in payments_ref.order_by('date', direction='DESCENDING').stream():
            p_data = doc.to_dict()
            p_data['id'] = doc.id
            p_date = p_data.get('date')
            
            # Logic Changed: Use explicit 'archived' flag. 
            # If a payment is archived, it's history. If not, it's active.
            if not p_data.get('archived'):
                total_paid += float(p_data.get('amount', 0))
            else:
                 # Mark as archived/history for UI
                 p_data['is_history'] = True
                 
            payments.append(p_data)
            
        fee_amount = float(student.get('fee_amount', 0))
        balance = fee_amount - total_paid

        # Fetch attendance (Optimize: Limit to recent docs for main view, though we need to parse them)
        attendance_ref = student_ref.collection('attendance')
        # We fetch a reasonable buffer (e.g. 15 days) to ensure we get 10 trips
        # Firestore querying limitations mean we can't easily query 'inside' the doc structure for trips.
        # So we fetch recent days.
        attendance_records = []
        try:
            # Assuming 'date' field exists for sorting.
            q = attendance_ref.order_by('date', direction='DESCENDING').limit(20)
            for doc in q.stream():
                if doc.id == 'stats': continue
                a_data = doc.to_dict()
                a_data['id'] = doc.id
                
                # Transform Day Record into Trip Records
                date = a_data.get('date')
                
                # Morning Trip
                if a_data.get('morning_status') in ['Present', 'exited']: # Check for existence
                     attendance_records.append({
                         'date': date,
                         'check_in': a_data.get('morning_time', '-'),
                         'check_out': a_data.get('morning_exit_time', '-'), # Hypothetical field
                         'type': 'Morning',
                         'timestamp': f"{date} {a_data.get('morning_time', '00:00')}" # Helper for sort
                     })
                     
                # Evening Trip
                if a_data.get('evening_status') in ['Present', 'exited']:
                     attendance_records.append({
                         'date': date,
                         'check_in': a_data.get('evening_time', '-'),
                         'check_out': a_data.get('evening_exit_time', '-'),
                         'type': 'Evening',
                         'timestamp': f"{date} {a_data.get('evening_time', '00:00')}"
                     })
        except Exception as e:
            print(f"Error fetching attendance: {e}")
        
        # Sort by timestamp descending
        attendance_records.sort(key=lambda x: x['timestamp'], reverse=True)
        
        # Slice Top 10
        recent_attendance = attendance_records[:10]

        # Fetch Organization Settings for Payment Type
        org_ref = db.collection('organizations').document(uid)
        org_doc = org_ref.get()
        org_payment_type = 'Monthly' # Default
        if org_doc.exists:
            org_data = org_doc.to_dict()
            org_payment_type = org_data.get('feeDetails', 'Monthly')

        return render_template('student_details.html', student=student, payments=payments, total_paid=total_paid, balance=balance, attendance_records=recent_attendance, buses=buses, routes=routes, org_payment_type=org_payment_type)
    else:
        return "Student not found", 404

@students_bp.route('/student_details/<student_id>/attendance')
def student_attendance_history(student_id):
    if 'user' not in session: return redirect(url_for('auth.login'))
    uid = session.get('uid')
    db = get_db()
    student_ref = db.collection('organizations').document(uid).collection('students').document(student_id)
    student = student_ref.get().to_dict()
    
    if not student:
        return "Student not found", 404
    student['id'] = student_id
    
    attendance_records = []
    try:
        attendance_ref = student_ref.collection('attendance').order_by('date', direction='DESCENDING').limit(100) # Fetch more for full history
        for doc in attendance_ref.stream():
            if doc.id == 'stats': continue
            a_data = doc.to_dict()
            
            date = a_data.get('date')
             # Morning Trip
            if a_data.get('morning_status'):
                 attendance_records.append({
                     'date': date,
                     'check_in': a_data.get('morning_time', '-'),
                     'check_out': a_data.get('morning_exit_time', '-'),
                     'type': 'Morning',
                     'timestamp': f"{date} {a_data.get('morning_time', '00:00')}"
                 })
            # Evening Trip
            if a_data.get('evening_status'):
                 attendance_records.append({
                     'date': date,
                     'check_in': a_data.get('evening_time', '-'),
                     'check_out': a_data.get('evening_exit_time', '-'),
                     'type': 'Evening',
                     'timestamp': f"{date} {a_data.get('evening_time', '00:00')}"
                 })
                 
        attendance_records.sort(key=lambda x: x['timestamp'], reverse=True)
    except Exception as e:
        print(f"Error fetching full attendance: {e}")
        
    return render_template('student_attendance_history.html', student=student, attendance_records=attendance_records)
