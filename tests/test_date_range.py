import unittest
import sys
import os
import json
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from extensions import db
from models import User, Task

class DateRangeTestCase(unittest.TestCase):
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
        u = User(username='test', email='test@example.com', full_name='Test User')
        u.set_password('password')
        db.session.add(u)
        db.session.commit()
        
        # Create a task completed TODAY at 23:00 (11 PM)
        # If the bug exists (end_date defaults to 00:00), this task will be excluded.
        today = datetime.now().replace(hour=23, minute=0, second=0, microsecond=0)
        
        t1 = Task(
            title='Late Task', 
            due_date=today, 
            creator_id=u.id,
            status='Completed',
            completed_at=today,
            completed_by_id=u.id
        )
        t1.assignees.append(u)
        db.session.add(t1)
        db.session.commit()
        
        self.today_str = today.strftime('%Y-%m-%d')

    def login(self):
        return self.client.post('/login', data=dict(
            username='test',
            password='password'
        ), follow_redirects=True)

    def test_reports_includes_late_task(self):
        self.login()
        
        # Request report for today
        response = self.client.post('/api/reports/data', json={
            'start_date': self.today_str,
            'end_date': self.today_str
        })
        data = response.get_json()
        
        # Check global stats
        self.assertEqual(data['global_stats']['completed'], 1, "Should have 1 completed task")
        
        # Check trend data
        # The date should be in the dates list
        self.assertIn(self.today_str, data['trend']['dates'])
        
        # Find the index of today
        idx = data['trend']['dates'].index(self.today_str)
        count = data['trend']['completed_counts'][idx]
        
        self.assertEqual(count, 1, "Trend should show 1 completed task for today")

if __name__ == '__main__':
    unittest.main()
