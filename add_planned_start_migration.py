"""
Migration script to add planned_start_date column to Task table.
"""
from app import app
from extensions import db

def run_migration():
    with app.app_context():
        conn = db.engine.connect()
        
        try:
            conn.execute(db.text('ALTER TABLE task ADD COLUMN IF NOT EXISTS planned_start_date TIMESTAMP'))
            print("[OK] Added column: planned_start_date")
            conn.commit()
        except Exception as e:
            print(f"Error adding column: {e}")
        
        conn.close()
        print("[DONE] Migration completed!")

if __name__ == "__main__":
    run_migration()
