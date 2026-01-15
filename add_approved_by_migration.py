"""
Migration script to add approved_by_id and approved_at columns to task table.
This allows tracking who approved a task from review separately from who did the work.

Run with: python add_approved_by_migration.py
"""

from app import app
from extensions import db

def migrate():
    with app.app_context():
        # Add approved_by_id column
        try:
            db.session.execute(db.text('''
                ALTER TABLE task 
                ADD COLUMN IF NOT EXISTS approved_by_id INTEGER REFERENCES "user"(id)
            '''))
            print("[OK] Added approved_by_id column")
        except Exception as e:
            print(f"approved_by_id column: {e}")
        
        # Add approved_at column
        try:
            db.session.execute(db.text('''
                ALTER TABLE task 
                ADD COLUMN IF NOT EXISTS approved_at TIMESTAMP
            '''))
            print("[OK] Added approved_at column")
        except Exception as e:
            print(f"approved_at column: {e}")
        
        db.session.commit()
        print("\n[OK] Migration completed successfully!")
        print("   New fields: approved_by_id, approved_at")

if __name__ == '__main__':
    migrate()
