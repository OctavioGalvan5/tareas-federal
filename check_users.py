from app import app
from models import User
from extensions import db
import sys

def check_users():
    print("Checking database connection and users...")
    try:
        with app.app_context():
            # Test connection
            db.engine.connect()
            print("Connection successful.")
            
            # List users
            users = User.query.all()
            print(f"Total users: {len(users)}")
            for user in users:
                print(f"User: {user.username}, Email: {user.email}, Admin: {user.is_admin}")
                
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_users()
