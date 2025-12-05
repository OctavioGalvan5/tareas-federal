import unittest
from datetime import datetime, date
from app import create_app, db
from models import User, Task, Tag
from io import BytesIO

class TestPDFExportCalc(unittest.TestCase):
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
            task_a = Task(
                title='Task A', due_date=datetime.now(), 
                creator_id=user.id, time_spent=120, status='Completed'
            )
            task_a.tags.append(tag_a)
            
            task_b = Task(
                title='Task B', due_date=datetime.now(), 
                creator_id=user.id, time_spent=60, status='Completed'
            )
            task_b.tags.append(tag_b)
             
            # Set completed_at for trend charts
            task_a.completed_at = datetime.now()
            task_b.completed_at = datetime.now()
            
            db.session.add_all([task_a, task_b])
            db.session.commit()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_export_pdf_with_calc(self):
        import json
        # Simulate form data for export with calc tags (JSON lists)
        response = self.client.post('/reports/export', data={
            'start_date': date.today().strftime('%Y-%m-%d'),
            'end_date': date.today().strftime('%Y-%m-%d'),
            'include_kpis': 'true',
            'diff_tag_a': json.dumps([self.tag_a_id]),
            'diff_tag_b': json.dumps([self.tag_b_id])
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['Content-Type'], 'application/pdf')
        # We can't easily parse PDF content here, but if status is 200, it generated successfully without crashing.

if __name__ == '__main__':
    unittest.main()
