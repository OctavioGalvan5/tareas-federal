from app import create_app
from extensions import db
from sqlalchemy import text

app = create_app()

def migrate():
    with app.app_context():
        with db.engine.connect() as conn:
            # Check if columns exist
            result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='task'"))
            columns = [row[0] for row in result]
            
            if 'last_edited_by_id' not in columns:
                print("Adding last_edited_by_id column...")
                conn.execute(text('ALTER TABLE task ADD COLUMN last_edited_by_id INTEGER REFERENCES "user"(id)'))
            else:
                print("last_edited_by_id column already exists.")
                
            if 'last_edited_at' not in columns:
                print("Adding last_edited_at column...")
                conn.execute(text('ALTER TABLE task ADD COLUMN last_edited_at TIMESTAMP'))
            else:
                print("last_edited_at column already exists.")
                
            conn.commit()
            print("Migration completed successfully.")

if __name__ == '__main__':
    migrate()
