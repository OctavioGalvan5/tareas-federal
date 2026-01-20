"""
Migration to add process_event table for unified process history.
Run with: python add_process_event_migration.py
"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from extensions import db
from sqlalchemy import text

app = create_app()

with app.app_context():
    with db.engine.connect() as conn:
        # Create process_event table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS process_event (
                id SERIAL PRIMARY KEY,
                process_id INTEGER NOT NULL REFERENCES process(id),
                event_type VARCHAR(50) NOT NULL,
                description TEXT NOT NULL,
                user_id INTEGER REFERENCES "user"(id),
                task_id INTEGER REFERENCES task(id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                extra_data TEXT
            )
        """))
        print("[OK] Created process_event table")
        
        # Create index for faster queries
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_process_event_process_id ON process_event(process_id)
        """))
        print("[OK] Created index on process_id")
        
        conn.commit()
    
    print("[DONE] Migration completed successfully!")
