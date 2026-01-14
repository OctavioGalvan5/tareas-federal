from app import create_app, db
from sqlalchemy import text

app = create_app()

def add_status_comment_column():
    with app.app_context():
        # Check if column exists
        with db.engine.connect() as conn:
            result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='status_transition' AND column_name='comment'"))
            if result.fetchone():
                print("Column 'comment' already exists in 'status_transition' table.")
                return

            print("Adding 'comment' column to 'status_transition' table...")
            try:
                conn.execute(text("ALTER TABLE status_transition ADD COLUMN comment TEXT"))
                conn.commit()
                print("Column added successfully.")
            except Exception as e:
                print(f"Error adding column: {e}")

if __name__ == "__main__":
    add_status_comment_column()
