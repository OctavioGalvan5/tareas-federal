"""
Migration: Add area_id column to TaskTemplate table and assign Federal area

This migration:
1. Adds area_id column to TaskTemplate table (if not exists)
2. Assigns all existing templates to Federal area
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
            db.session.commit()
            
            # Step 1: Add area_id column to TaskTemplate table
            print("\nStep 1: Adding area_id column to TaskTemplate table...")
            try:
                db.session.execute(text("ALTER TABLE task_template ADD COLUMN area_id INTEGER REFERENCES area(id)"))
                db.session.commit()
                print("✓ Added area_id column to TaskTemplate table")
            except Exception as e:
                db.session.rollback()
                if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
                    print("Column area_id already exists in TaskTemplate table (OK)")
                else:
                    print(f"Warning: {e}")
            
            # Step 2: Update all templates to Federal area
            print("\nStep 2: Assigning Federal area to all templates...")
            db.session.execute(text(f"UPDATE task_template SET area_id = {federal_id} WHERE area_id IS NULL"))
            db.session.commit()
            
            # Count templates
            count = db.session.execute(text("SELECT COUNT(*) FROM task_template WHERE area_id IS NOT NULL")).scalar()
            print(f"✓ Templates with area_id: {count}")
            
            print("\n✅ Migration completed successfully!")
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"ERROR: {e}")
            return False

if __name__ == '__main__':
    print("=" * 50)
    print("Migration: Add area_id to TaskTemplate table")
    print("=" * 50)
    
    confirm = input("\nThis will add area_id column to TaskTemplate table and assign Federal to all templates.\nContinue? (yes/no): ")
    
    if confirm.lower() == 'yes':
        run_migration()
    else:
        print("Migration cancelled.")
