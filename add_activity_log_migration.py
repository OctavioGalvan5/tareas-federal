"""
Migration script to add activity_log table
Run this script once to add the ActivityLog table to the database.
"""

from app import app, db
from models import ActivityLog

def run_migration():
    with app.app_context():
        # Create the activity_log table
        db.create_all()
        print("✅ ActivityLog table created successfully!")

if __name__ == '__main__':
    run_migration()
