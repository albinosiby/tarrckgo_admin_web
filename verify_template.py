
import os
import sys
from jinja2 import Environment, FileSystemLoader

# Add project root
sys.path.append(os.getcwd())

# Setup Jinja2
template_dir = os.path.join(os.getcwd(), 'app', 'templates')
env = Environment(loader=FileSystemLoader(template_dir))

# Mock context
context = {
    'session': {'user': 'test'},
    'url_for': lambda x, **kwargs: f"/mock/{x}",
    'get_flashed_messages': lambda **kwargs: [],
    'bus': {
        'id': 'bus123',
        'bus_number': 'B1',
        'registration_no': 'KL-01-AB-1234',
        'capacity': 50,
        'driver_name_display': 'John Doe',
        'route': 'Route A',
        'last_service_date': None
    },
    'drivers': [],
    'routes': [],
    'trip_history': [],
    'boarded_students': [
        {
            'full_name': 'Student A',
            'roll_number': '101',
            'parent_phone': '1234567890',
            'profile_photo_url': 'http://example.com/photo.jpg'
        },
        {
            'full_name': 'Student B',
            'roll_number': '102',
            'parent_phone': None,
            'profile_photo_url': None
        }
    ]
}

try:
    template = env.get_template('bus_details.html')
    output = template.render(context)
    print("Template rendered successfully!")
    
    if "Current Boarded Students" in output:
        print("FOUND: Current Boarded Students section")
        
    if "Student A" in output:
        print("FOUND: Student A")
        
    if "Student B" in output:
        print("FOUND: Student B")
        
except Exception as e:
    print(f"Error rendering template: {e}")
