"""
Migration script to add parent_id column to task table for task hierarchy support.
Run this script once to update the database schema.
"""

from app import app
from extensions import db
from models import Task

def migrate():
    with app.app_context():
        print("Starting migration: Adding parent_id to task table...")
        
        try:
            # Check if column already exists
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('task')]
            
            if 'parent_id' in columns:
                print("[OK] Column 'parent_id' already exists. Skipping migration.")
                return
            
            # Add parent_id column
            with db.engine.connect() as conn:
                conn.execute(db.text('ALTER TABLE task ADD COLUMN parent_id INTEGER'))
                conn.execute(db.text('ALTER TABLE task ADD FOREIGN KEY (parent_id) REFERENCES task(id)'))
                conn.commit()
            
            print("[OK] Migration completed successfully!")
            print("  - Added 'parent_id' column to 'task' table")
            print("  - Added foreign key constraint")
            
        except Exception as e:
            print(f"[ERROR] Migration failed: {e}")
            raise

if __name__ == '__main__':
    migrate()
