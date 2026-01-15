"""
Migration: Add SubtaskTemplate table and template_id to RecurringTask

This migration:
1. Creates the subtask_template table for hierarchical subtasks in templates
2. Adds template_id column to recurring_task table

Run this script once to update the database schema.
"""

import os
import sys
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from extensions import db

def run_migration():
    app = create_app()
    
    with app.app_context():
        # Get raw connection for executing DDL
        connection = db.engine.connect()
        
        print("Starting migration: SubtaskTemplate + RecurringTask.template_id")
        print("=" * 60)
        
        # 1. Create subtask_template table
        print("\n1. Creating subtask_template table...")
        try:
            connection.execute(db.text("""
                CREATE TABLE IF NOT EXISTS subtask_template (
                    id SERIAL PRIMARY KEY,
                    template_id INTEGER NOT NULL REFERENCES task_template(id) ON DELETE CASCADE,
                    parent_id INTEGER REFERENCES subtask_template(id) ON DELETE CASCADE,
                    title VARCHAR(200) NOT NULL,
                    description TEXT,
                    priority VARCHAR(20) DEFAULT 'Normal',
                    days_offset INTEGER DEFAULT 0,
                    "order" INTEGER DEFAULT 0
                )
            """))
            connection.commit()
            print("   [OK] subtask_template table created successfully")
        except Exception as e:
            if 'already exists' in str(e).lower():
                print("   [INFO] subtask_template table already exists, skipping")
            else:
                print(f"   [ERROR] Error creating subtask_template: {e}")
                raise
        
        # 2. Add template_id to recurring_task
        print("\n2. Adding template_id column to recurring_task...")
        try:
            connection.execute(db.text("""
                ALTER TABLE recurring_task 
                ADD COLUMN IF NOT EXISTS template_id INTEGER REFERENCES task_template(id)
            """))
            connection.commit()
            print("   [OK] template_id column added successfully")
        except Exception as e:
            if 'already exists' in str(e).lower() or 'duplicate column' in str(e).lower():
                print("   [INFO] template_id column already exists, skipping")
            else:
                print(f"   [ERROR] Error adding template_id: {e}")
                raise
        
        # 3. Create index for faster lookups
        print("\n3. Creating indexes...")
        try:
            connection.execute(db.text("""
                CREATE INDEX IF NOT EXISTS idx_subtask_template_template_id 
                ON subtask_template(template_id)
            """))
            connection.execute(db.text("""
                CREATE INDEX IF NOT EXISTS idx_subtask_template_parent_id 
                ON subtask_template(parent_id)
            """))
            connection.commit()
            print("   [OK] Indexes created successfully")
        except Exception as e:
            print(f"   [INFO] Index creation note: {e}")
        
        connection.close()
        
        print("\n" + "=" * 60)
        print("Migration completed successfully!")
        print("=" * 60)

if __name__ == '__main__':
    run_migration()
