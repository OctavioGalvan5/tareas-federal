"""
Migration script to add multi-area support to the database.
This script:
1. Creates the 'area' table
2. Creates the 'user_areas' association table
3. Adds 'role' column to user table
4. Adds 'area_id' column to task, expiration, and recurring_task tables
5. Creates default areas (Federal, Contable, Legajos, Provincial)
6. Assigns all existing tasks and users to the 'Federal' area

Run this script ONCE after deploying the updated models.py
Usage: python add_areas_migration.py
"""

import os
import sys
from datetime import datetime

# Add parent directory to path so we can import our app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from extensions import db
from sqlalchemy import text, inspect

def run_migration():
    app = create_app()
    
    with app.app_context():
        # Get database connection
        connection = db.engine.connect()
        inspector = inspect(db.engine)
        existing_tables = inspector.get_table_names()
        
        print("=" * 60)
        print("MIGRATION: Adding Multi-Area Support")
        print("=" * 60)
        
        # Step 1: Create 'area' table if it doesn't exist
        if 'area' not in existing_tables:
            print("\n[1/6] Creating 'area' table...")
            connection.execute(text("""
                CREATE TABLE area (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) UNIQUE NOT NULL,
                    description TEXT,
                    color VARCHAR(7) NOT NULL DEFAULT '#6366f1',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            connection.commit()
            print("      ✓ 'area' table created")
        else:
            print("\n[1/6] 'area' table already exists, skipping...")
        
        # Step 2: Create 'user_areas' association table
        if 'user_areas' not in existing_tables:
            print("\n[2/6] Creating 'user_areas' table...")
            connection.execute(text("""
                CREATE TABLE user_areas (
                    user_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
                    area_id INTEGER NOT NULL REFERENCES area(id) ON DELETE CASCADE,
                    PRIMARY KEY (user_id, area_id)
                )
            """))
            connection.commit()
            print("      ✓ 'user_areas' table created")
        else:
            print("\n[2/6] 'user_areas' table already exists, skipping...")
        
        # Step 3: Add 'role' column to user table
        user_columns = [col['name'] for col in inspector.get_columns('user')]
        if 'role' not in user_columns:
            print("\n[3/6] Adding 'role' column to 'user' table...")
            connection.execute(text("""
                ALTER TABLE "user" ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'usuario'
            """))
            connection.commit()
            print("      ✓ 'role' column added to 'user' table")
        else:
            print("\n[3/6] 'role' column already exists in 'user', skipping...")
        
        # Step 4: Add 'area_id' column to task, expiration, recurring_task
        print("\n[4/6] Adding 'area_id' columns to tables...")
        
        tables_to_update = ['task', 'expiration', 'recurring_task']
        for table_name in tables_to_update:
            if table_name in existing_tables:
                columns = [col['name'] for col in inspector.get_columns(table_name)]
                if 'area_id' not in columns:
                    connection.execute(text(f"""
                        ALTER TABLE {table_name} ADD COLUMN area_id INTEGER REFERENCES area(id)
                    """))
                    connection.commit()
                    print(f"      ✓ 'area_id' column added to '{table_name}'")
                else:
                    print(f"      - 'area_id' already exists in '{table_name}', skipping...")
        
        # Step 5: Create default areas
        print("\n[5/6] Creating default areas...")
        default_areas = [
            ('Federal', 'Área Federal - Derechos federales', '#3b82f6'),
            ('Contable', 'Área Contable - Contabilidad y finanzas', '#10b981'),
            ('Legajos', 'Área Legajos - Gestión de legajos', '#f59e0b'),
            ('Provincial', 'Área Provincial - Derechos provinciales', '#8b5cf6'),
        ]
        
        for name, description, color in default_areas:
            # Check if area already exists
            result = connection.execute(text("SELECT id FROM area WHERE name = :name"), {"name": name})
            if result.fetchone() is None:
                connection.execute(text("""
                    INSERT INTO area (name, description, color) VALUES (:name, :description, :color)
                """), {"name": name, "description": description, "color": color})
                connection.commit()
                print(f"      ✓ Created area: {name}")
            else:
                print(f"      - Area '{name}' already exists, skipping...")
        
        # Step 6: Assign existing data to 'Federal' area
        print("\n[6/6] Assigning existing data to 'Federal' area...")
        
        # Get Federal area ID
        result = connection.execute(text("SELECT id FROM area WHERE name = 'Federal'"))
        federal_area = result.fetchone()
        
        if federal_area:
            federal_id = federal_area[0]
            
            # Assign all tasks without area to Federal
            connection.execute(text("""
                UPDATE task SET area_id = :area_id WHERE area_id IS NULL
            """), {"area_id": federal_id})
            connection.commit()
            print(f"      ✓ Assigned tasks to Federal area")
            
            # Assign all expirations without area to Federal
            connection.execute(text("""
                UPDATE expiration SET area_id = :area_id WHERE area_id IS NULL
            """), {"area_id": federal_id})
            connection.commit()
            print(f"      ✓ Assigned expirations to Federal area")
            
            # Assign all recurring_tasks without area to Federal
            connection.execute(text("""
                UPDATE recurring_task SET area_id = :area_id WHERE area_id IS NULL
            """), {"area_id": federal_id})
            connection.commit()
            print(f"      ✓ Assigned recurring tasks to Federal area")
            
            # Assign all users to Federal area (if not already assigned to any area)
            result = connection.execute(text("SELECT id FROM \"user\""))
            users = result.fetchall()
            for user in users:
                user_id = user[0]
                # Check if user already has areas
                result = connection.execute(text("""
                    SELECT COUNT(*) FROM user_areas WHERE user_id = :user_id
                """), {"user_id": user_id})
                count = result.fetchone()[0]
                if count == 0:
                    connection.execute(text("""
                        INSERT INTO user_areas (user_id, area_id) VALUES (:user_id, :area_id)
                    """), {"user_id": user_id, "area_id": federal_id})
                    connection.commit()
            print(f"      ✓ Assigned users to Federal area")
        
        connection.close()
        
        print("\n" + "=" * 60)
        print("MIGRATION COMPLETE!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Redeploy the application in Dokploy")
        print("2. Test that the dashboard loads correctly")
        print("3. Go to Admin > Manage Areas to see the new areas")
        print("4. Go to Admin > Manage Users to assign users to areas and roles")

if __name__ == '__main__':
    run_migration()
