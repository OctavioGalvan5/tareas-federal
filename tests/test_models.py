import unittest
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import create_app
from extensions import db
from models import User, Task
from datetime import datetime, timedelta

class ModelTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.client = self.app.test_client()
        
        with self.app.app_context():
            db.create_all()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_user_creation(self):
        with self.app.app_context():
            u = User(username='test', email='test@example.com', full_name='Test User')
            u.set_password('password')
            db.session.add(u)
            db.session.commit()
            
            self.assertTrue(u.check_password('password'))
            self.assertFalse(u.check_password('wrong'))

    def test_task_creation_and_ordering(self):
        with self.app.app_context():
            u = User(username='test', email='test@example.com', full_name='Test User')
            u.set_password('password')
            db.session.add(u)
            db.session.commit()
            
            # Create tasks with different due dates
            t1 = Task(title='Task 1', due_date=datetime.now() + timedelta(days=2), creator_id=u.id)
            t2 = Task(title='Task 2', due_date=datetime.now() + timedelta(days=1), creator_id=u.id)
            
            db.session.add(t1)
            db.session.add(t2)
            db.session.commit()
            
            # Query ordered by due_date
            tasks = Task.query.order_by(Task.due_date.asc()).all()
            
            # t2 should be first because it's due sooner
            self.assertEqual(tasks[0].title, 'Task 2')
            self.assertEqual(tasks[1].title, 'Task 1')

if __name__ == '__main__':
    unittest.main()
