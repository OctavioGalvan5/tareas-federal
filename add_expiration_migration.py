"""
Migration script to add the Expiration table for the expiration calendar feature.
Run this script once to add the new table to an existing database.
"""
from app import create_app
from extensions import db
from models import Expiration, expiration_tags

def run_migration():
    app = create_app()
    
    with app.app_context():
        # Create the expiration_tags table and Expiration table
        # This only creates tables that don't exist yet
        db.create_all()
        print("[OK] Migration completed successfully!")
        print("   - Created 'expiration' table")
        print("   - Created 'expiration_tags' association table")

if __name__ == '__main__':
    run_migration()
