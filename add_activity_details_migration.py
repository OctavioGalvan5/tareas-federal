
from app import create_app, db
from sqlalchemy import text

app = create_app()

def migrate():
    with app.app_context():
        try:
            # Check if column exists (Postgres compatible)
            with db.engine.connect() as conn:
                # Use standard SQL to check column existence
                # Note: wrapping column name in quotes might be needed depending on case settings, 
                # but usually lower case is fine in default Postgres
                
                # Try adding the column directly - if it exists, grab the specific error
                # Or query information_schema. A simple approach for a quick script:
                try:
                    conn.execute(text("ALTER TABLE activity_log ADD COLUMN details TEXT"))
                    conn.commit()
                    print("Column 'details' added successfully.")
                except Exception as e:
                    if "duplicate column name" in str(e) or "already exists" in str(e):
                         print("Column 'details' already exists (caught exception).")
                    else:
                         # Re-raise if it's a different error (or try inspection)
                         print(f"Attempting inspection due to: {e}")
                         # Fallback inspection
                         result = conn.execute(text(
                            "SELECT column_name FROM information_schema.columns WHERE table_name='activity_log'"
                         ))
                         columns = [row[0] for row in result.fetchall()]
                         if 'details' in columns:
                             print("Column 'details' confirmed to exist.")
                         else:
                             raise e

        except Exception as e:
            print(f"Error during migration: {str(e)}")

if __name__ == '__main__':
    migrate()
