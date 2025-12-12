"""
Migration script to add enabled, enabled_at, and enabled_by_task_id columns to the Task table.
Run this script once to update the database schema.
"""

from app import create_app
from extensions import db
from sqlalchemy import text

def run_migration():
    app = create_app()
    with app.app_context():
        # Add enabled column (default True for existing tasks)
        try:
            db.session.execute(text('ALTER TABLE task ADD COLUMN enabled BOOLEAN DEFAULT TRUE'))
            db.session.commit()
            print("Added 'enabled' column")
        except Exception as e:
            db.session.rollback()
            print(f"Column 'enabled' might already exist: {e}")
        
        # Add enabled_at column (use TIMESTAMP for PostgreSQL)
        try:
            db.session.execute(text('ALTER TABLE task ADD COLUMN enabled_at TIMESTAMP'))
            db.session.commit()
            print("Added 'enabled_at' column")
        except Exception as e:
            db.session.rollback()
            print(f"Column 'enabled_at' might already exist: {e}")
        
        # Add enabled_by_task_id column
        try:
            db.session.execute(text('ALTER TABLE task ADD COLUMN enabled_by_task_id INTEGER'))
            db.session.commit()
            print("Added 'enabled_by_task_id' column")
        except Exception as e:
            db.session.rollback()
            print(f"Column 'enabled_by_task_id' might already exist: {e}")
        
        # Update all existing tasks to have enabled=True
        try:
            db.session.execute(text('UPDATE task SET enabled = TRUE WHERE enabled IS NULL'))
            db.session.commit()
            print("Updated existing tasks to enabled=True")
        except Exception as e:
            db.session.rollback()
            print(f"Error updating existing tasks: {e}")
        
        print("Migration completed successfully!")

if __name__ == '__main__':
    run_migration()
