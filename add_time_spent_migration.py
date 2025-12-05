"""
Migration script to add time_spent column to Task and TaskTemplate tables.
Run this script once to update the database schema.

Usage: python add_time_spent_migration.py
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from app import create_app
from extensions import db
from sqlalchemy import text

def run_migration():
    app = create_app()
    
    with app.app_context():
        connection = db.engine.connect()
        
        print("Starting migration: Adding time_spent column...")
        
        try:
            # Add time_spent column to task table
            print("  -> Adding time_spent to 'task' table...")
            connection.execute(text("""
                ALTER TABLE task ADD COLUMN IF NOT EXISTS time_spent INTEGER;
            """))
            print("     Done!")
            
            # Add time_spent column to task_template table
            print("  -> Adding time_spent to 'task_template' table...")
            connection.execute(text("""
                ALTER TABLE task_template ADD COLUMN IF NOT EXISTS time_spent INTEGER DEFAULT 0;
            """))
            print("     Done!")
            
            connection.commit()
            print("\n✅ Migration completed successfully!")
            
        except Exception as e:
            print(f"\n❌ Migration failed: {e}")
            print("\nNote: If columns already exist, this is expected. The app should still work.")
            
        finally:
            connection.close()

if __name__ == "__main__":
    run_migration()
