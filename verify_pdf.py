import sys
import os
import json

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from app import create_app
from extensions import db
from models import User, Tag

def verify_pdf_export():
    app = create_app()
    with app.app_context():
        # Create a test client
        client = app.test_client()
        
        # Login as admin
        client.post('/login', data=dict(
            username='admin',
            password='admin'
        ), follow_redirects=True)
        
        # Get a tag ID
        tag = Tag.query.first()
        tag_id = tag.id if tag else 1
        
        # Call export API with filters
        response = client.post('/reports/export', data={
            'user_ids': json.dumps([]),
            'tag_ids': json.dumps([tag_id]),
            'status': 'Completed',
            'start_date': '2025-01-01',
            'end_date': '2025-12-31'
        })
        
        print(f"Response Status: {response.status_code}")
        print(f"Content Type: {response.headers['Content-Type']}")
        
        if response.status_code == 200 and 'application/pdf' in response.headers['Content-Type']:
            print("SUCCESS: PDF generated successfully with filters.")
            # Optionally save it to check manually
            with open('test_report_filters.pdf', 'wb') as f:
                f.write(response.data)
            print("Saved to test_report_filters.pdf")
        else:
            print("FAILURE: Could not generate PDF.")

if __name__ == '__main__':
    verify_pdf_export()
