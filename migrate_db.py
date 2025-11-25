"""
Database migration script to add completed_by_id and completed_at columns to task table.
Run this once to update your database schema.
"""
import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def migrate_database():
    """Add completion tracking columns to task table"""
    
    # Get database URL from environment
    database_url = os.environ.get('DATABASE_URL')
    
    if not database_url:
        print("[ERROR] DATABASE_URL not found in .env file")
        return False
    
    print("[*] Connecting to database...")
    
    try:
        # Connect to database
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        print("[OK] Connected successfully!")
        print("[*] Running migration...")
        
        # Check if columns already exist
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'task' 
            AND column_name IN ('completed_by_id', 'completed_at');
        """)
        
        existing_columns = [row[0] for row in cursor.fetchall()]
        
        if 'completed_by_id' in existing_columns and 'completed_at' in existing_columns:
            print("[INFO] Columns already exist. Migration not needed.")
            cursor.close()
            conn.close()
            return True
        
        # Add the new columns
        migration_sql = """
            ALTER TABLE task 
            ADD COLUMN IF NOT EXISTS completed_by_id INTEGER REFERENCES "user"(id),
            ADD COLUMN IF NOT EXISTS completed_at TIMESTAMP;
        """
        
        cursor.execute(migration_sql)
        conn.commit()
        
        print("[OK] Migration completed successfully!")
        print("     - Added column: completed_by_id (INTEGER, references user.id)")
        print("     - Added column: completed_at (TIMESTAMP)")
        
        cursor.close()
        conn.close()
        
        return True
        
    except psycopg2.Error as e:
        print(f"[ERROR] Database error: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("DATABASE MIGRATION: Add Completion Tracking")
    print("=" * 60)
    print()
    
    success = migrate_database()
    
    print()
    if success:
        print("[SUCCESS] Migration completed! You can now start the application.")
    else:
        print("[FAILED] Migration failed. Please check the error messages above.")
    print()
