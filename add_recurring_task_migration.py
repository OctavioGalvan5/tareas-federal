"""
Database migration script to add RecurringTask table and related columns.
Compatible with PostgreSQL and SQLite.
Run this once to update the database schema.
"""
import os
import sys
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from extensions import db
from sqlalchemy import text, inspect

def run_migration():
    app = create_app()
    
    with app.app_context():
        inspector = inspect(db.engine)
        existing_tables = inspector.get_table_names()
        
        # Detect if PostgreSQL or SQLite
        db_url = str(db.engine.url)
        is_postgres = 'postgresql' in db_url.lower() or 'postgres' in db_url.lower()
        
        print(f"Database type: {'PostgreSQL' if is_postgres else 'SQLite'}")
        print("Starting migration for RecurringTask feature...")
        
        # 1. Create recurring_task table if it doesn't exist
        if 'recurring_task' not in existing_tables:
            print("  Creating 'recurring_task' table...")
            if is_postgres:
                db.session.execute(text("""
                    CREATE TABLE recurring_task (
                        id SERIAL PRIMARY KEY,
                        title VARCHAR(200) NOT NULL,
                        description TEXT,
                        priority VARCHAR(20) NOT NULL DEFAULT 'Normal',
                        recurrence_type VARCHAR(20) NOT NULL,
                        days_of_week VARCHAR(20),
                        day_of_month INTEGER,
                        due_time TIME NOT NULL,
                        start_date DATE NOT NULL,
                        end_date DATE,
                        time_spent INTEGER DEFAULT 0,
                        is_active BOOLEAN DEFAULT TRUE,
                        creator_id INTEGER NOT NULL REFERENCES "user"(id),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_generated_date DATE
                    )
                """))
            else:
                db.session.execute(text("""
                    CREATE TABLE recurring_task (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title VARCHAR(200) NOT NULL,
                        description TEXT,
                        priority VARCHAR(20) NOT NULL DEFAULT 'Normal',
                        recurrence_type VARCHAR(20) NOT NULL,
                        days_of_week VARCHAR(20),
                        day_of_month INTEGER,
                        due_time TIME NOT NULL,
                        start_date DATE NOT NULL,
                        end_date DATE,
                        time_spent INTEGER DEFAULT 0,
                        is_active BOOLEAN DEFAULT 1,
                        creator_id INTEGER NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        last_generated_date DATE,
                        FOREIGN KEY (creator_id) REFERENCES user(id)
                    )
                """))
            print("  [OK] Table 'recurring_task' created")
        else:
            print("  Table 'recurring_task' already exists, skipping...")
        
        # 2. Create recurring_task_assignments table
        if 'recurring_task_assignments' not in existing_tables:
            print("  Creating 'recurring_task_assignments' table...")
            if is_postgres:
                db.session.execute(text("""
                    CREATE TABLE recurring_task_assignments (
                        recurring_task_id INTEGER NOT NULL REFERENCES recurring_task(id) ON DELETE CASCADE,
                        user_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
                        PRIMARY KEY (recurring_task_id, user_id)
                    )
                """))
            else:
                db.session.execute(text("""
                    CREATE TABLE recurring_task_assignments (
                        recurring_task_id INTEGER NOT NULL,
                        user_id INTEGER NOT NULL,
                        PRIMARY KEY (recurring_task_id, user_id),
                        FOREIGN KEY (recurring_task_id) REFERENCES recurring_task(id) ON DELETE CASCADE,
                        FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
                    )
                """))
            print("  [OK] Table 'recurring_task_assignments' created")
        else:
            print("  Table 'recurring_task_assignments' already exists, skipping...")
        
        # 3. Create recurring_task_tags table
        if 'recurring_task_tags' not in existing_tables:
            print("  Creating 'recurring_task_tags' table...")
            if is_postgres:
                db.session.execute(text("""
                    CREATE TABLE recurring_task_tags (
                        recurring_task_id INTEGER NOT NULL REFERENCES recurring_task(id) ON DELETE CASCADE,
                        tag_id INTEGER NOT NULL REFERENCES tag(id) ON DELETE CASCADE,
                        PRIMARY KEY (recurring_task_id, tag_id)
                    )
                """))
            else:
                db.session.execute(text("""
                    CREATE TABLE recurring_task_tags (
                        recurring_task_id INTEGER NOT NULL,
                        tag_id INTEGER NOT NULL,
                        PRIMARY KEY (recurring_task_id, tag_id),
                        FOREIGN KEY (recurring_task_id) REFERENCES recurring_task(id) ON DELETE CASCADE,
                        FOREIGN KEY (tag_id) REFERENCES tag(id) ON DELETE CASCADE
                    )
                """))
            print("  [OK] Table 'recurring_task_tags' created")
        else:
            print("  Table 'recurring_task_tags' already exists, skipping...")
        
        # 4. Add recurring_task_id column to task table
        task_columns = [col['name'] for col in inspector.get_columns('task')]
        if 'recurring_task_id' not in task_columns:
            print("  Adding 'recurring_task_id' column to 'task' table...")
            db.session.execute(text("""
                ALTER TABLE task ADD COLUMN recurring_task_id INTEGER REFERENCES recurring_task(id)
            """))
            print("  [OK] Column 'recurring_task_id' added to 'task' table")
        else:
            print("  Column 'recurring_task_id' already exists in 'task' table, skipping...")
        
        db.session.commit()
        print("\n[OK] Migration completed successfully!")


if __name__ == '__main__':
    run_migration()
