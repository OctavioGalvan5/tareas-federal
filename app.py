import os
from flask import Flask, render_template, redirect, url_for, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from extensions import db, login_manager

# Initialize extensions
# db = SQLAlchemy() -> Moved to extensions.py
# login_manager = LoginManager() -> Moved to extensions.py

def create_app():
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///local.db')
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
        db.create_all()

    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
