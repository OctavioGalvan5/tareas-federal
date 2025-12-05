import unittest
from datetime import datetime, timedelta
from app import create_app, db
from models import User, Task, Tag

class TestCalcDifference(unittest.TestCase):
    def setUp(self):
        self.app = create_app(test_config={
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'
        })
        self.client = self.app.test_client()
        
        with self.app.app_context():
            db.create_all()
            
            # Create user
            user = User(username='test', email='test@example.com', full_name='Test User', is_admin=True)
            user.set_password('password')
            db.session.add(user)
            db.session.commit()
            self.user_id = user.id
            
            # Login
            with self.client.session_transaction() as sess:
                sess['_user_id'] = str(user.id)
                sess['_fresh'] = True

            # Create tags
            tag_a = Tag(name='Tag A', color='#000', created_by_id=user.id)
            tag_b = Tag(name='Tag B', color='#000', created_by_id=user.id)
            db.session.add_all([tag_a, tag_b])
            db.session.commit()
            
            self.tag_a_id = tag_a.id
            self.tag_b_id = tag_b.id
            
            # Create tasks
            # Task A: 120 mins (2 hours)
            task_a = Task(
                title='Task A', due_date=datetime.now(), 
                creator_id=user.id, time_spent=120, status='Completed'
            )
            task_a.tags.append(tag_a)
            
            # Task B: 60 mins (1 hour)
            task_b = Task(
                title='Task B', due_date=datetime.now(), 
                creator_id=user.id, time_spent=60, status='Completed'
            )
            task_b.tags.append(tag_b)
            
            db.session.add_all([task_a, task_b])
            db.session.commit()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_calculate_difference(self):
        response = self.client.post('/api/reports/calculate_difference', json={
            'tag_a_id': self.tag_a_id,
            'tag_b_id': self.tag_b_id
        })
        
        data = response.get_json()
        self.assertEqual(data['time_a'], 120)
        self.assertEqual(data['time_b'], 60)
        self.assertEqual(data['diff'], 60)
        self.assertEqual(data['formatted'], '1h 0m')
        
    def test_calculate_negative_difference(self):
        # Swap tags
        response = self.client.post('/api/reports/calculate_difference', json={
            'tag_a_id': self.tag_b_id,
            'tag_b_id': self.tag_a_id
        })
        
        data = response.get_json()
        self.assertEqual(data['diff'], -60)
        self.assertEqual(data['formatted'], '- 1h 0m')

if __name__ == '__main__':
    unittest.main()
