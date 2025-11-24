from app import app
from models import User
from extensions import db
import sys

def create_test_user():
    print("Creating test user 'testadmin'...")
    try:
        with app.app_context():
            # Check if exists
            if User.query.filter_by(username='testadmin').first():
                print("User 'testadmin' already exists. Resetting password...")
                user = User.query.filter_by(username='testadmin').first()
                user.set_password('testpass123')
            else:
                user = User(username='testadmin', email='test@example.com', full_name='Test Admin', is_admin=True)
                user.set_password('testpass123')
                db.session.add(user)
            
            db.session.commit()
            print("SUCCESS: User 'testadmin' created/updated with password 'testpass123'.")
            
            # Verify immediately
            u = User.query.filter_by(username='testadmin').first()
            if u and u.check_password('testpass123'):
                print("VERIFICATION: Password check PASSED.")
            else:
                print("VERIFICATION: Password check FAILED.")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    create_test_user()
