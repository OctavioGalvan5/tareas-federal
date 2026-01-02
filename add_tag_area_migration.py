"""
Migration: Add area_id column to Tag table and assign Federal area

This migration:
1. Adds area_id column to Tag table (if not exists)
2. Assigns all existing tags to Federal area
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from sqlalchemy import text

def run_migration():
    app = create_app()
    
    with app.app_context():
        try:
            # Find Federal area ID
            result = db.session.execute(text("SELECT id FROM area WHERE name = 'Federal'"))
            federal_row = result.fetchone()
            if not federal_row:
                print("ERROR: Area 'Federal' not found!")
                return False
            
            federal_id = federal_row[0]
            print(f"Found Federal area with ID: {federal_id}")
            db.session.commit()  # Commit the SELECT
            
            # Step 1: Add area_id column to Tag table
            print("\nStep 1: Adding area_id column to Tag table...")
            try:
                db.session.execute(text("ALTER TABLE tag ADD COLUMN area_id INTEGER REFERENCES area(id)"))
                db.session.commit()
                print("✓ Added area_id column to Tag table")
            except Exception as e:
                db.session.rollback()
                if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
                    print("Column area_id already exists in Tag table (OK)")
                else:
                    print(f"Warning: {e}")
            
            # Step 2: Update all tags to Federal area
            print("\nStep 2: Assigning Federal area to all tags...")
            result = db.session.execute(text(f"UPDATE tag SET area_id = {federal_id} WHERE area_id IS NULL"))
            db.session.commit()
            
            # Count tags
            count = db.session.execute(text("SELECT COUNT(*) FROM tag WHERE area_id IS NOT NULL")).scalar()
            print(f"✓ Tags with area_id: {count}")
            
            print("\n✅ Migration completed successfully!")
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"ERROR: {e}")
            return False

if __name__ == '__main__':
    print("=" * 50)
    print("Migration: Add area_id to Tag table")
    print("=" * 50)
    
    confirm = input("\nThis will add area_id column to Tag table and assign Federal to all tags.\nContinue? (yes/no): ")
    
    if confirm.lower() == 'yes':
        run_migration()
    else:
        print("Migration cancelled.")
