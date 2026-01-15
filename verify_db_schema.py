from app import create_app
from extensions import db
from sqlalchemy import inspect, text

app = create_app()

with app.app_context():
    inspector = inspect(db.engine)
    
    print("\n--- Checking task_template columns ---")
    columns = inspector.get_columns('task_template')
    col_names = [c['name'] for c in columns]
    print(f"Columns: {col_names}")
    if 'start_time' in col_names:
        print("SUCCESS: start_time exists in task_template")
    else:
        print("FAILURE: start_time MISSING in task_template")
        
    print("\n--- Checking subtask_template columns ---")
    columns = inspector.get_columns('subtask_template')
    col_names = [c['name'] for c in columns]
    print(f"Columns: {col_names}")
    if 'start_time' in col_names:
        print("SUCCESS: start_time exists in subtask_template")
    else:
        print("FAILURE: start_time MISSING in subtask_template")
        
    # Attempt Raw SQL Check
    print("\n--- Raw SQL Check ---")
    try:
        with db.engine.connect() as conn:
            result = conn.execute(text("SELECT start_time FROM task_template LIMIT 1"))
            print("Select start_time executed successfully.")
    except Exception as e:
        print(f"Select start_time FAILED: {e}")
