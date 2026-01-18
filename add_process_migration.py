"""
Migration script to add Process System tables.
Creates: process_type, process tables
Modifies: task (adds process_id column)

Run with: python add_process_migration.py
"""

from app import create_app
from extensions import db
from sqlalchemy import text, inspect
from datetime import datetime

def run_migration():
    app = create_app()
    
    with app.app_context():
        inspector = inspect(db.engine)
        existing_tables = inspector.get_table_names()
        
        print("=== Process System Migration ===")
        print(f"Existing tables: {existing_tables}")
        
        # 1. Create process_type table
        if 'process_type' not in existing_tables:
            print("\n[1/3] Creating 'process_type' table...")
            db.session.execute(text("""
                CREATE TABLE process_type (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    description TEXT,
                    color VARCHAR(7) NOT NULL DEFAULT '#6366f1',
                    icon VARCHAR(50) DEFAULT 'fa-folder',
                    area_id INTEGER NOT NULL REFERENCES area(id),
                    created_by_id INTEGER NOT NULL REFERENCES "user"(id),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE,
                    template_id INTEGER REFERENCES task_template(id),
                    CONSTRAINT uq_process_type_name_area UNIQUE (name, area_id)
                )
            """))
            db.session.commit()
            print("   [OK] 'process_type' table created successfully")
        else:
            print("\n[1/3] 'process_type' table already exists, skipping...")
        
        # 2. Create process table
        if 'process' not in existing_tables:
            print("\n[2/3] Creating 'process' table...")
            db.session.execute(text("""
                CREATE TABLE process (
                    id SERIAL PRIMARY KEY,
                    process_type_id INTEGER NOT NULL REFERENCES process_type(id),
                    name VARCHAR(200) NOT NULL,
                    description TEXT,
                    status VARCHAR(20) NOT NULL DEFAULT 'Active',
                    area_id INTEGER NOT NULL REFERENCES area(id),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    due_date TIMESTAMP NOT NULL,
                    created_by_id INTEGER NOT NULL REFERENCES "user"(id),
                    completed_by_id INTEGER REFERENCES "user"(id)
                )
            """))
            db.session.commit()
            print("   [OK] 'process' table created successfully")
        else:
            print("\n[2/3] 'process' table already exists, skipping...")
        
        # 3. Add process_id column to task table
        task_columns = [col['name'] for col in inspector.get_columns('task')]
        
        if 'process_id' not in task_columns:
            print("\n[3/3] Adding 'process_id' column to 'task' table...")
            db.session.execute(text("""
                ALTER TABLE task ADD COLUMN process_id INTEGER REFERENCES process(id)
            """))
            db.session.commit()
            print("   [OK] 'process_id' column added to 'task' table successfully")
        else:
            print("\n[3/3] 'process_id' column already exists in 'task' table, skipping...")
        
        print("\n=== Migration Complete ===")
        print("Process System tables are ready!")
        
        # Verify
        print("\n--- Verification ---")
        inspector = inspect(db.engine)
        
        if 'process_type' in inspector.get_table_names():
            cols = [c['name'] for c in inspector.get_columns('process_type')]
            print(f"process_type columns: {cols}")
        
        if 'process' in inspector.get_table_names():
            cols = [c['name'] for c in inspector.get_columns('process')]
            print(f"process columns: {cols}")
        
        task_cols = [c['name'] for c in inspector.get_columns('task')]
        if 'process_id' in task_cols:
            print(f"task.process_id: [OK] present")

if __name__ == '__main__':
    run_migration()
