import unittest
import sys
import os
import json
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from extensions import db
from models import User, Task, Tag

class ReportsTestCase(unittest.TestCase):
    def setUp(self):
        # Set env var to force sqlite memory BEFORE create_app
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
        # Create User
        u = User(username='test', email='test@example.com', full_name='Test User')
        u.set_password('password')
        db.session.add(u)
        
        # Create Tags
        tag1 = Tag(name='Urgent', color='#ff0000', created_by=u)
        tag2 = Tag(name='Backend', color='#00ff00', created_by=u)
        db.session.add(tag1)
        db.session.add(tag2)
        
        db.session.commit()
        
        # Create Tasks
        # Task 1: Completed, Tag 1
        t1 = Task(
            title='Task 1', 
            due_date=datetime.now(), 
            creator_id=u.id,
            status='Completed',
            completed_at=datetime.now(),
            completed_by_id=u.id
        )
        t1.assignees.append(u)
        t1.tags.append(tag1)
        
        # Task 2: Pending, Tag 2
        t2 = Task(
            title='Task 2', 
            due_date=datetime.now(), 
            creator_id=u.id,
            status='Pending'
        )
        t2.assignees.append(u)
        t2.tags.append(tag2)
        
        db.session.add(t1)
        db.session.add(t2)
        db.session.commit()
        
        self.user_id = u.id
        self.tag1_id = tag1.id
        self.tag2_id = tag2.id

    def login(self):
        return self.client.post('/login', data=dict(
            username='test',
            password='password'
        ), follow_redirects=True)

    def test_reports_data_no_filters(self):
        self.login()
        response = self.client.post('/api/reports/data', json={})
        data = response.get_json()
        
        self.assertEqual(data['global_stats']['completed'], 1)
        self.assertEqual(data['global_stats']['pending'], 1)
        self.assertEqual(len(data['user_stats']), 1)
        self.assertEqual(data['user_stats'][0]['completed'], 1)

    def test_reports_data_tag_filter(self):
        self.login()
        # Filter by Tag 1 (should show 1 completed, 0 pending)
        response = self.client.post('/api/reports/data', json={
            'tag_ids': [self.tag1_id]
        })
        data = response.get_json()
        
        self.assertEqual(data['global_stats']['completed'], 1)
        self.assertEqual(data['global_stats']['pending'], 0)
        
        # Filter by Tag 2 (should show 0 completed, 1 pending)
        response = self.client.post('/api/reports/data', json={
            'tag_ids': [self.tag2_id]
        })
        data = response.get_json()
        
        self.assertEqual(data['global_stats']['completed'], 0)
        self.assertEqual(data['global_stats']['pending'], 1)

    def test_reports_data_status_filter(self):
        self.login()
        # Filter by Status 'Completed'
        response = self.client.post('/api/reports/data', json={
            'status': 'Completed'
        })
        data = response.get_json()
        
        self.assertEqual(data['global_stats']['completed'], 1)
        self.assertEqual(data['global_stats']['pending'], 0)

    def test_reports_charts_data(self):
        self.login()
        response = self.client.post('/api/reports/data', json={})
        data = response.get_json()
        
        # Check Trend Data
        self.assertIn('trend', data)
        self.assertIn('dates', data['trend'])
        self.assertIn('completed_counts', data['trend'])
        
        # Check Employee Trend Data
        self.assertIn('employee_trend', data)
        self.assertTrue(len(data['employee_trend']) > 0)
        self.assertEqual(data['employee_trend'][0]['label'], 'Test User')
        
        # Check Tag Trend Data
        self.assertIn('tag_trend', data)
        # Should have at least one tag trend dataset (for tag1 which is completed)
        # Tag 2 is pending so it won't show in trend (trend is for completed tasks)
        self.assertTrue(len(data['tag_trend']) > 0)

if __name__ == '__main__':
    unittest.main()
