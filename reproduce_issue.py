
import os
from app import create_app
from extensions import db
from models import User, Task, Area
from sqlalchemy import or_

def reproduce():
    # Use a fresh app instance for testing
    app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'})
    
    with app.app_context():
        db.create_all()
        
        # Create Areas
        try:
            area_a = Area(name='Accounting', color='#ff0000')
            db.session.add(area_a)
            db.session.commit()
            
            area_b = Area(name='IT', color='#00ff00')
            db.session.add(area_b)
            db.session.commit()
            
            # Create Users
            supervisor_a = User(
                username='sup_a', 
                email='sup_a@example.com',
                full_name='Supervisor A', 
                role='supervisor',
                is_admin=False
            )
            supervisor_a.set_password('password')
            supervisor_a.areas.append(area_a)
            db.session.add(supervisor_a)
            db.session.commit()
            
            admin = User(
                username='admin', 
                email='admin@example.com',
                full_name='Admin', 
                role='gerente',
                is_admin=True
            )
            admin.set_password('password')
            db.session.add(admin)
            db.session.commit()
            
            # Create Tasks
            from datetime import datetime
            now = datetime.utcnow()
            
            task_a = Task(
                title='Task in Accounting',
                status='Pending',
                due_date=now,
                creator_id=admin.id,
                area_id=area_a.id
            )
            
            task_b = Task(
                title='Task in IT',
                status='Pending',
                due_date=now,
                creator_id=admin.id,
                area_id=area_b.id
            )
            
            db.session.add(task_a)
            db.session.add(task_b)
            db.session.commit()
            
            print("Setup Complete.")
            
            # --- SIMULATE LOGIC ---
            current_user = supervisor_a
            
            print(f"\nUser: {current_user.username}")
            print(f"Role: {current_user.role}")
            print(f"Is Admin: {current_user.is_admin}")
            print(f"Areas: {[a.name for a in current_user.areas]}")
            
            # Logic from routes.py 'scrum_board'
            query = Task.query.filter(Task.status != 'Anulado')
            
            # Role-based visibility
            user_area_ids = [a.id for a in current_user.areas]
            
            if current_user.can_only_see_own_tasks():
                print("Branch: Own Tasks Only")
            elif current_user.can_see_all_areas():
                print("Branch: All Areas")
            else:
                print("Branch: Supervisor Area Filter (ELSE)")
                if user_area_ids:
                    print(f"Filtering by Area IDs: {user_area_ids}")
                    query = query.filter(Task.area_id.in_(user_area_ids))
                else:
                    query = query.filter(Task.area_id == -1)
            
            results = query.all()
            
            print(f"\nVisible Tasks ({len(results)}):")
            for t in results:
                print(f" - {t.title} (Area: {t.area.name})")
            
            # Verify
            visible_titles = [t.title for t in results]
            if 'Task in IT' in visible_titles:
                print("\n[FAIL] Supervisor A can see 'Task in IT'!")
            else:
                print("\n[PASS] Supervisor A cannot see 'Task in IT'.")
                
            if 'Task in Accounting' not in visible_titles:
                 print("[FAIL] Supervisor A CANNOT see their own Area task!")
            else:
                 print("[PASS] Supervisor A sees 'Task in Accounting'.")
                 
            # --- TEST CASE 2: Supervisor with is_admin=True ---
            print("\n--- TEST CASE 2: Supervisor with is_admin=True ---")
            supervisor_admin = User(
                username='sup_admin', 
                email='sup_admin@example.com',
                full_name='Super Admin', 
                role='supervisor',
                is_admin=True
            )
            supervisor_admin.set_password('password')
            supervisor_admin.areas.append(area_a)
            db.session.add(supervisor_admin)
            db.session.commit()
            
            # Switch user
            current_user = supervisor_admin
            print(f"User: {current_user.username}, Role: {current_user.role}, Is Admin: {current_user.is_admin}")
            print(f"Can see all areas? {current_user.can_see_all_areas()}")
            
            # Same logic
            query = Task.query.filter(Task.status != 'Anulado')
            user_area_ids = [a.id for a in current_user.areas]
            
            if current_user.can_only_see_own_tasks():
                print("Branch: Own Tasks Only")
            elif current_user.can_see_all_areas():
                print("Branch: All Areas")
            else:
                print("Branch: Supervisor Area Filter (ELSE)")
                if user_area_ids:
                    query = query.filter(Task.area_id.in_(user_area_ids))
                else:
                    query = query.filter(Task.area_id == -1)
            
            results = query.all()
            visible_titles = [t.title for t in results]
            if 'Task in IT' in visible_titles:
                print("[CONFIRMED] Supervisor with is_admin=True SEES 'Task in IT'.")
            else:
                print("[passed] Supervisor with is_admin=True does NOT see 'Task in IT'.")

        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    reproduce()
