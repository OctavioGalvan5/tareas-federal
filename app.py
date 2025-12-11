import os
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv
import pytz

# Load environment variables
load_dotenv()

from extensions import db, login_manager

# Buenos Aires timezone
BUENOS_AIRES_TZ = pytz.timezone('America/Argentina/Buenos_Aires')

def to_buenos_aires(dt):
    """Convert a datetime to Buenos Aires timezone."""
    if dt is None:
        return None
    # If the datetime is naive (no timezone), assume it's UTC
    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt)
    return dt.astimezone(BUENOS_AIRES_TZ)

# Initialize extensions
# db = SQLAlchemy() -> Moved to extensions.py
# login_manager = LoginManager() -> Moved to extensions.py

def create_app(test_config=None):
    app = Flask(__name__)
    
    # Fix for running behind a reverse proxy (Traefik/Nginx)
    # This ensures Flask uses HTTPS in url_for() when behind a proxy
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
    
    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///local.db')

    if test_config:
        app.config.update(test_config)

    print(f"DEBUG: Database URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Initialize extensions with app
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'

    with app.app_context():
        # Import parts of our application
        from models import User, Task
        from routes import main_bp, auth_bp, admin_bp
        
        # Register Blueprints
        app.register_blueprint(main_bp)
        app.register_blueprint(auth_bp)
        app.register_blueprint(admin_bp)

        # Create database tables for development (if they don't exist)
        # db.create_all() -> Removed for production performance. Run migrations manually.
    
    # Register custom Jinja2 filters
    app.jinja_env.filters['to_buenos_aires'] = to_buenos_aires

    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
