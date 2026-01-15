from app import create_app, db
from sqlalchemy import text

app = create_app()

def migrate():
    with app.app_context():
        # Add columns to task_template
        try:
            with db.engine.connect() as conn:
                conn.execute(text("ALTER TABLE task_template ADD COLUMN start_time TIME"))
                conn.execute(text("ALTER TABLE task_template ADD COLUMN start_days_offset INTEGER DEFAULT 0"))
                print("Added columns to task_template")
        except Exception as e:
            print(f"Error updating task_template: {e}")

        # Add columns to subtask_template
        try:
            with db.engine.connect() as conn:
                conn.execute(text("ALTER TABLE subtask_template ADD COLUMN start_time TIME"))
                conn.execute(text("ALTER TABLE subtask_template ADD COLUMN start_days_offset INTEGER DEFAULT 0"))
                print("Added columns to subtask_template")
        except Exception as e:
            print(f"Error updating subtask_template: {e}")
            
        db.session.commit()

if __name__ == '__main__':
    migrate()
