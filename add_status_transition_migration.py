"""
Migration script to add status_transition table for tracking task status history.
Run this script once to add the table.
"""
from app import app
from extensions import db
from sqlalchemy import text

def run_migration():
    with app.app_context():
        with db.engine.connect() as conn:
            # Create status_transition table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS status_transition (
                    id SERIAL PRIMARY KEY,
                    task_id INTEGER NOT NULL REFERENCES task(id) ON DELETE CASCADE,
                    from_status VARCHAR(50) NOT NULL,
                    to_status VARCHAR(50) NOT NULL,
                    changed_by_id INTEGER NOT NULL REFERENCES "user"(id),
                    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            # Create index for faster queries
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_status_transition_task_id ON status_transition(task_id)
            """))
            
            conn.commit()
            print("Successfully created status_transition table")

if __name__ == '__main__':
    run_migration()
