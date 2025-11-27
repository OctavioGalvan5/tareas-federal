import sys
import os
from datetime import datetime, timedelta
import random

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from app import create_app
from extensions import db
from models import User, Task, Tag

def seed_data():
    app = create_app()
    with app.app_context():
        print("Cleaning up existing data...")
        # Clear association tables first
        db.session.execute(db.text("DELETE FROM task_assignments"))
        db.session.execute(db.text("DELETE FROM task_tags"))
        db.session.commit()
        
        # Delete all tasks
        Task.query.delete()
        # Delete all tags
        Tag.query.delete()
        
        db.session.commit()
        print("Data cleaned.")

        # Ensure we have users
        usernames = ['admin', 'user1', 'user2']
        users = []
        for username in usernames:
            user = User.query.filter_by(username=username).first()
            if not user:
                print(f"Creating user {username}...")
                user = User(username=username, email=f'{username}@example.com', full_name=f'User {username}')
                user.set_password('password')
                if username == 'admin':
                    user.is_admin = True
                    user.full_name = 'Admin User'
                db.session.add(user)
                db.session.commit() # Commit to get ID
            users.append(user)
        
        print(f"Using users: {[u.username for u in users]}")

        # Create Tags
        tags_data = [
            ('Urgente', '#ef4444'), # Red
            ('Frontend', '#3b82f6'), # Blue
            ('Backend', '#10b981'), # Green
            ('Diseño', '#f59e0b'), # Orange
            ('Testing', '#8b5cf6')  # Purple
        ]
        
        tags = []
        for name, color in tags_data:
            tag = Tag(name=name, color=color, created_by_id=users[0].id)
            db.session.add(tag)
            tags.append(tag)
        
        db.session.commit()
        print(f"Created {len(tags)} tags.")

        # Create Tasks
        # We want a mix of Pending and Completed.
        # Completed tasks should have completed_at spread over the last 30 days.
        
        tasks_created = 0
        
        # 1. Completed Tasks (Historical data for trends)
        start_date = datetime.now() - timedelta(days=30)
        
        for i in range(30): # For each of the last 30 days
            # Randomly create 0-3 completed tasks per day
            num_tasks = random.randint(0, 3)
            current_date = start_date + timedelta(days=i)
            
            for _ in range(num_tasks):
                creator = random.choice(users)
                assignee = random.choice(users)
                tag = random.choice(tags)
                
                task = Task(
                    title=f"Tarea completada {tasks_created + 1}",
                    description="Tarea de prueba generada automáticamente.",
                    priority=random.choice(['Normal', 'Alta', 'Baja']),
                    status='Completed',
                    due_date=current_date, # Due date around that time
                    creator_id=creator.id,
                    completed_by_id=assignee.id,
                    completed_at=current_date.replace(hour=random.randint(9, 18), minute=random.randint(0, 59))
                )
                task.assignees.append(assignee)
                task.tags.append(tag)
                
                # Maybe add a second tag sometimes
                if random.random() > 0.7:
                    task.tags.append(random.choice(tags))
                
                db.session.add(task)
                tasks_created += 1
                
        # 2. Pending Tasks (Future due dates)
        for i in range(10):
            creator = random.choice(users)
            assignee = random.choice(users)
            tag = random.choice(tags)
            
            due_date = datetime.now() + timedelta(days=random.randint(1, 14))
            
            task = Task(
                title=f"Tarea pendiente {i + 1}",
                description="Esta tarea está pendiente.",
                priority=random.choice(['Normal', 'Alta', 'Urgente']),
                status='Pending',
                due_date=due_date,
                creator_id=creator.id
            )
            task.assignees.append(assignee)
            task.tags.append(tag)
            
            db.session.add(task)
            tasks_created += 1

        db.session.commit()
        print(f"Successfully created {tasks_created} tasks.")

if __name__ == '__main__':
    seed_data()
