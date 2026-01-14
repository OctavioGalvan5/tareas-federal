import unittest
import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from extensions import db
from models import User, Task

class NotificationsTestCase(unittest.TestCase):
    def setUp(self):
        os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()
        
        with self.app.app_context():
            db.create_all()
            self.create_test_data()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def create_test_data(self):
        user = User(username='test', email='test@example.com', full_name='Test User')
        user.set_password('password')
        user.notifications_enabled = True # Ensure enabled
        db.session.add(user)
        db.session.commit()
        self.user_id = user.id

        # Due tomorrow (Due Soon)
        tomorrow = datetime.now() + timedelta(days=1)
        
        # Pending - Should show
        t1 = Task(title='Pending Task', due_date=tomorrow, creator_id=user.id, status='Pending', enabled=True)
        t1.assignees.append(user)
        
        # In Progress - Should show (NEW!)
        t2 = Task(title='InProgress Task', due_date=tomorrow, creator_id=user.id, status='In Progress', enabled=True)
        t2.assignees.append(user)
        
        # In Review - Should show (NEW!)
        t3 = Task(title='InReview Task', due_date=tomorrow, creator_id=user.id, status='In Review', enabled=True)
        t3.assignees.append(user)
        
        # Completed - Should NOT show
        t4 = Task(title='Completed Task', due_date=tomorrow, creator_id=user.id, status='Completed', enabled=True)
        t4.assignees.append(user)
        
        # Anulado - Should NOT show
        t5 = Task(title='Anulado Task', due_date=tomorrow, creator_id=user.id, status='Anulado', enabled=True)
        t5.assignees.append(user)

        db.session.add_all([t1, t2, t3, t4, t5])
        db.session.commit()

    def login(self):
        return self.client.post('/login', data=dict(
            username='test',
            password='password'
        ), follow_redirects=True)

    def test_api_tasks_due_soon(self):
        self.login()
        response = self.client.get('/api/tasks/due_soon')
        data = response.get_json()
        
        tasks = data['tasks']
        titles = [t['title'] for t in tasks]
        
        self.assertIn('Pending Task', titles)
        self.assertIn('InProgress Task', titles)
        self.assertIn('InReview Task', titles)
        self.assertNotIn('Completed Task', titles)
        self.assertNotIn('Anulado Task', titles)

if __name__ == '__main__':
    unittest.main()
