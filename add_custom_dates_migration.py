"""
Migration script to add custom_dates column to recurring_task table.
Run this script once to add the new column for manual date selection feature.
"""
import os
import sys
from sqlalchemy import create_engine, text

def run_migration():
    """Add custom_dates column to recurring_task table."""
    database_url = os.environ.get('DATABASE_URL')
    
    if not database_url:
        print("ERROR: DATABASE_URL environment variable not set")
        sys.exit(1)
    
    engine = create_engine(database_url)
    
    with engine.connect() as conn:
        # Check if column already exists
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'recurring_task' AND column_name = 'custom_dates'
        """))
        
        if result.fetchone():
            print("Column 'custom_dates' already exists. Skipping migration.")
            return
        
        # Add custom_dates column
        print("Adding 'custom_dates' column to recurring_task table...")
        conn.execute(text("""
            ALTER TABLE recurring_task 
            ADD COLUMN custom_dates TEXT
        """))
        conn.commit()
        
        print("Migration completed successfully!")
        print("The 'custom_dates' column has been added to the recurring_task table.")

if __name__ == '__main__':
    run_migration()
