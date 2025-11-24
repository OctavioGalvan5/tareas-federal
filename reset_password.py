from app import app
from models import User
from extensions import db
import sys

def reset_password(username, new_password):
    print(f"Attempting to reset password for user: {username}")
    try:
        with app.app_context():
            user = User.query.filter_by(username=username).first()
            if user:
                user.set_password(new_password)
                db.session.commit()
                print(f"SUCCESS: Password for '{username}' has been updated.")
            else:
                print(f"ERROR: User '{username}' not found.")
                users = User.query.all()
                print(f"Available users: {[u.username for u in users]}")
                
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python reset_password.py <username> <new_password>")
    else:
        reset_password(sys.argv[1], sys.argv[2])
