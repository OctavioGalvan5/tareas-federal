"""
Database migration script to add tags tables.
"""
import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def migrate_database():
    """Create tag and task_tags tables"""
    
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
        
        # Check if tag table already exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'tag'
            );
        """)
        
        if cursor.fetchone()[0]:
            print("[INFO] Tag table already exists. Skipping migration.")
            cursor.close()
            conn.close()
            return True
        
        # Create tag table
        print("[*] Creating tag table...")
        tag_table_sql = """
            CREATE TABLE tag (
                id SERIAL PRIMARY KEY,
                name VARCHAR(50) UNIQUE NOT NULL,
                color VARCHAR(7) NOT NULL,
                created_by_id INTEGER REFERENCES "user"(id) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """
        cursor.execute(tag_table_sql)
        print("[OK] Tag table created")
        
        # Create task_tags association table
        print("[*] Creating task_tags table...")
        task_tags_sql = """
            CREATE TABLE task_tags (
                task_id INTEGER REFERENCES task(id) ON DELETE CASCADE,
                tag_id INTEGER REFERENCES tag(id) ON DELETE CASCADE,
                PRIMARY KEY (task_id, tag_id)
            );
        """
        cursor.execute(task_tags_sql)
        print("[OK] Task_tags table created")
        
        # Create some default tags
        print("[*] Creating default tags...")
        default_tags = [
            ('Civil', '#2563eb'),
            ('Penal', '#dc2626'),
            ('Laboral', '#16a34a'),
            ('Familia', '#db2777'),
            ('Urgente', '#ea580c'),
            ('Facturable', '#65a30d')
        ]
        
        # Get first admin user
        cursor.execute("SELECT id FROM \"user\" WHERE is_admin = TRUE LIMIT 1;")
        result = cursor.fetchone()
        if result:
            admin_id = result[0]
            for tag_name, tag_color in default_tags:
                cursor.execute(
                    "INSERT INTO tag (name, color, created_by_id) VALUES (%s, %s, %s);",
                    (tag_name, tag_color, admin_id)
                )
            print(f"[OK] Created {len(default_tags)} default tags")
        else:
            print("[INFO] No admin user found, skipping default tags creation")
        
        conn.commit()
        
        print("[OK] Migration completed successfully!")
        print("     - Created table: tag")
        print("     - Created table: task_tags")
        print(f"     - Created {len(default_tags) if result else 0} default tags")
        
        cursor.close()
        conn.close()
        
        return True
        
    except psycopg2.Error as e:
        print(f"[ERROR] Database error: {e}")
        if conn:
            conn.rollback()
        return False
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("DATABASE MIGRATION: Add Tags System")
    print("=" * 60)
    print()
    
    success = migrate_database()
    
    print()
    if success:
        print("[SUCCESS] Migration completed!")
    else:
        print("[FAILED] Migration failed. Please check the error messages above.")
    print()
