"""
Migration script to add process transfer functionality.
Creates:
1. process_involved_areas table (for multi-area visibility)
2. process_transfer table (for transfer history)
"""

from app import app
from extensions import db
from sqlalchemy import inspect, text

def run_migration():
    with app.app_context():
        inspector = inspect(db.engine)
        existing_tables = inspector.get_table_names()
        
        # Create process_involved_areas table
        if 'process_involved_areas' not in existing_tables:
            print("Creating 'process_involved_areas' table...")
            db.session.execute(text("""
                CREATE TABLE process_involved_areas (
                    process_id INTEGER NOT NULL,
                    area_id INTEGER NOT NULL,
                    PRIMARY KEY (process_id, area_id),
                    FOREIGN KEY (process_id) REFERENCES process(id) ON DELETE CASCADE,
                    FOREIGN KEY (area_id) REFERENCES area(id) ON DELETE CASCADE
                )
            """))
            print("[OK] Table 'process_involved_areas' created successfully")
        else:
            print("Table 'process_involved_areas' already exists, skipping...")
        
        # Create process_transfer table
        if 'process_transfer' not in existing_tables:
            print("Creating 'process_transfer' table...")
            db.session.execute(text("""
                CREATE TABLE process_transfer (
                    id SERIAL PRIMARY KEY,
                    process_id INTEGER NOT NULL,
                    from_area_id INTEGER NOT NULL,
                    to_area_id INTEGER NOT NULL,
                    transferred_by_id INTEGER NOT NULL,
                    transferred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    comment TEXT,
                    FOREIGN KEY (process_id) REFERENCES process(id),
                    FOREIGN KEY (from_area_id) REFERENCES area(id),
                    FOREIGN KEY (to_area_id) REFERENCES area(id),
                    FOREIGN KEY (transferred_by_id) REFERENCES "user"(id)
                )
            """))
            print("[OK] Table 'process_transfer' created successfully")
        else:
            print("Table 'process_transfer' already exists, skipping...")
        
        db.session.commit()
        print("\n[SUCCESS] Migration completed successfully!")

if __name__ == '__main__':
    run_migration()
