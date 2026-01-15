from app import create_app, db
from sqlalchemy import text

app = create_app()

def migrate():
    with app.app_context():
        print("Starting migration fix...")
        # Use begin() for auto-commit transaction
        with db.engine.begin() as conn:
            print("Adding columns to task_template...")
            conn.execute(text("ALTER TABLE task_template ADD COLUMN IF NOT EXISTS start_time TIME"))
            conn.execute(text("ALTER TABLE task_template ADD COLUMN IF NOT EXISTS start_days_offset INTEGER DEFAULT 0"))
            
            print("Adding columns to subtask_template...")
            conn.execute(text("ALTER TABLE subtask_template ADD COLUMN IF NOT EXISTS start_time TIME"))
            conn.execute(text("ALTER TABLE subtask_template ADD COLUMN IF NOT EXISTS start_days_offset INTEGER DEFAULT 0"))
            
        print("Migration committed successfully.")

if __name__ == '__main__':
    migrate()
