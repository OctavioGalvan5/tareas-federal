from app import create_app
from extensions import db
from models import Area, User

app = create_app()
with app.app_context():
    supervisor_area = Area.query.filter_by(name='Supervisores').first()
    if supervisor_area:
        print(f"Area 'Supervisores' exists with ID: {supervisor_area.id}")
    else:
        print("Area 'Supervisores' does NOT exist.")

    supervisors = User.query.filter_by(role='supervisor').all()
    print(f"Found {len(supervisors)} supervisors.")
    for s in supervisors:
        area_names = [a.name for a in s.areas]
        print(f"Supervisor: {s.username}, Areas: {area_names}")
