"""
Migration: Assign Federal area to all tasks/expirations and add area_id to Tags

This migration:
1. Assigns all tasks without area_id to Federal area
2. Assigns all expirations without area_id to Federal area
3. Adds area_id column to Tag table
4. Assigns all existing tags to Federal area
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from models import Task, Tag, Expiration, Area
from sqlalchemy import text

def run_migration():
    app = create_app()
    
    with app.app_context():
        # 1. Find Federal area
        federal_area = Area.query.filter_by(name='Federal').first()
        if not federal_area:
            print("ERROR: Area 'Federal' not found!")
            return False
        
        federal_id = federal_area.id
        print(f"Found Federal area with ID: {federal_id}")
        
        # 2. Update tasks without area_id
        tasks_without_area = Task.query.filter(Task.area_id == None).count()
        print(f"Tasks without area_id: {tasks_without_area}")
        
        if tasks_without_area > 0:
            Task.query.filter(Task.area_id == None).update({Task.area_id: federal_id})
            print(f"✓ Updated {tasks_without_area} tasks to Federal area")
        
        # 3. Update expirations without area_id
        expirations_without_area = Expiration.query.filter(Expiration.area_id == None).count()
        print(f"Expirations without area_id: {expirations_without_area}")
        
        if expirations_without_area > 0:
            Expiration.query.filter(Expiration.area_id == None).update({Expiration.area_id: federal_id})
            print(f"✓ Updated {expirations_without_area} expirations to Federal area")
        
        # 4. Add area_id to Tag table if not exists
        try:
            # Check if column exists
            result = db.session.execute(text("SELECT area_id FROM tag LIMIT 1"))
            print("Column area_id already exists in Tag table")
        except Exception:
            # Column doesn't exist, add it
            print("Adding area_id column to Tag table...")
            db.session.execute(text("ALTER TABLE tag ADD COLUMN area_id INTEGER REFERENCES area(id)"))
            print("✓ Added area_id column to Tag table")
        
        # 5. Update all tags without area_id to Federal
        db.session.execute(text(f"UPDATE tag SET area_id = {federal_id} WHERE area_id IS NULL"))
        tags_updated = db.session.execute(text("SELECT COUNT(*) FROM tag WHERE area_id IS NOT NULL")).scalar()
        print(f"✓ Updated tags to Federal area (total with area: {tags_updated})")
        
        # Commit all changes
        db.session.commit()
        print("\n✅ Migration completed successfully!")
        
        # Summary
        print("\n--- Summary ---")
        print(f"Tasks with Federal area: {Task.query.filter_by(area_id=federal_id).count()}")
        print(f"Expirations with Federal area: {Expiration.query.filter_by(area_id=federal_id).count()}")
        
        return True

if __name__ == '__main__':
    print("=" * 50)
    print("Migration: Assign Federal Area to Existing Data")
    print("=" * 50)
    
    confirm = input("\nThis will assign all tasks, expirations and tags without area to Federal.\nContinue? (yes/no): ")
    
    if confirm.lower() == 'yes':
        run_migration()
    else:
        print("Migration cancelled.")
