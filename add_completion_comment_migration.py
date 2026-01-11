from app import app, db
from sqlalchemy import text

def migrate():
    with app.app_context():
        try:
            # Add completion_comment column
            with db.engine.connect() as conn:
                conn.execute(text("ALTER TABLE task ADD COLUMN completion_comment TEXT"))
                conn.commit()
            print("Successfully added completion_comment column to task table")
        except Exception as e:
            print(f"Error adding column: {str(e)}")
            # If column exists it might fail, which is fine
            
if __name__ == '__main__':
    migrate()
