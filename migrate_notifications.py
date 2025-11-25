"""
Database migration script to add notifications_enabled column to user table.
"""
import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def migrate_database():
    """Add notifications_enabled column to user table"""
    
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
        
        # Check if column already exists
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'user' 
            AND column_name = 'notifications_enabled';
        """)
        
        if cursor.fetchone():
            print("[INFO] Column already exists. Migration not needed.")
            cursor.close()
            conn.close()
            return True
        
        # Add the new column
        migration_sql = """
            ALTER TABLE "user" 
            ADD COLUMN notifications_enabled BOOLEAN DEFAULT TRUE;
        """
        
        cursor.execute(migration_sql)
        conn.commit()
        
        print("[OK] Migration completed successfully!")
        print("     - Added column: notifications_enabled (BOOLEAN, default=TRUE)")
        
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
    print("DATABASE MIGRATION: Add Notifications Preference")
    print("=" * 60)
    print()
    
    success = migrate_database()
    
    print()
    if success:
        print("[SUCCESS] Migration completed!")
    else:
        print("[FAILED] Migration failed. Please check the error messages above.")
    print()
