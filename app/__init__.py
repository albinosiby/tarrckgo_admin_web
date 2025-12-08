from flask import Flask
from config import Config
from app.services.firebase_service import init_firebase

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize Firebase
    init_firebase(app)

    # Register Blueprints
    from app.routes.auth import auth_bp
    from app.routes.main import main_bp
    from app.routes.students import students_bp
    from app.routes.buses import buses_bp
    from app.routes.drivers import drivers_bp
    from app.routes.routes_mgmt import routes_bp
    from app.routes.api import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(students_bp)
    app.register_blueprint(buses_bp)
    app.register_blueprint(drivers_bp)
    app.register_blueprint(routes_bp)
    app.register_blueprint(api_bp)

    return app
