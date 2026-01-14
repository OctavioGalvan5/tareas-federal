"""
Migration script to add Scrum board status tracking fields to Task table.
Adds: started_at, started_by_id, in_review_at, in_review_by_id
Backfills existing data based on current status.
"""
from app import app
from extensions import db
from datetime import datetime, time, timedelta

def run_migration():
    with app.app_context():
        # 1. Add new columns if they don't exist
        conn = db.engine.connect()
        
        # Check and add columns
        columns_to_add = [
            ("started_at", "TIMESTAMP"),
            ("started_by_id", "INTEGER REFERENCES \"user\"(id)"),
            ("in_review_at", "TIMESTAMP"),
            ("in_review_by_id", "INTEGER REFERENCES \"user\"(id)")
        ]
        
        for col_name, col_type in columns_to_add:
            try:
                conn.execute(db.text(f'ALTER TABLE task ADD COLUMN IF NOT EXISTS {col_name} {col_type}'))
                print(f"[OK] Added column: {col_name}")
            except Exception as e:
                print(f"Column {col_name} may already exist: {e}")
        
        conn.commit()
        
        # 2. Backfill existing Completed tasks
        # For completed tasks: set all transition timestamps to completed_at
        result = conn.execute(db.text("""
            UPDATE task 
            SET started_at = completed_at,
                started_by_id = completed_by_id,
                in_review_at = completed_at,
                in_review_by_id = completed_by_id
            WHERE status = 'Completed' 
            AND completed_at IS NOT NULL
            AND started_at IS NULL
        """))
        print(f"[OK] Backfilled {result.rowcount} completed tasks")
        
        conn.commit()
        
        # 3. Count tasks by status for verification
        result = conn.execute(db.text("""
            SELECT status, COUNT(*) as count 
            FROM task 
            GROUP BY status
        """))
        print("\nTask count by status:")
        for row in result:
            print(f"   {row[0]}: {row[1]}")
        
        conn.close()
        print("\n[DONE] Migration completed successfully!")

if __name__ == "__main__":
    run_migration()
