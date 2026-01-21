"""
Migration script to add the task_attachment table for file attachments.
Run this script once to create the table.
"""
from extensions import db
from models import TaskAttachment
from sqlalchemy import inspect

def run_migration():
    """Add the task_attachment table if it doesn't exist."""
    inspector = inspect(db.engine)
    existing_tables = inspector.get_table_names()
    
    if 'task_attachment' not in existing_tables:
        # Create the table
        TaskAttachment.__table__.create(db.engine)
        print("✅ Table 'task_attachment' created successfully!")
    else:
        print("ℹ️ Table 'task_attachment' already exists.")

if __name__ == '__main__':
    from app import app
    with app.app_context():
        run_migration()
