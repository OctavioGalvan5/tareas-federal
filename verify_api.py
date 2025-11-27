import sys
import os
import json

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from app import create_app
from extensions import db
from models import User

def verify_api():
    app = create_app()
    with app.app_context():
        # Create a test client
        client = app.test_client()
        
        # Login as admin (created in seed_data)
        client.post('/login', data=dict(
            username='admin',
            password='admin'
        ), follow_redirects=True)
        
        # Call reports data API
        response = client.post('/api/reports/data', json={})
        data = response.get_json()
        
        print("Global Stats:", data['global_stats'])
        print("Trend Data Points:", len(data['trend']['dates']))
        print("Employee Trend Datasets:", len(data['employee_trend']))
        print("Tag Trend Datasets:", len(data['tag_trend']))
        
        # Check if we have actual data in trends
        total_trend_counts = sum(data['trend']['completed_counts'])
        print(f"Total Completed in Trend: {total_trend_counts}")
        
        if total_trend_counts > 0:
            print("SUCCESS: Trend data is present.")
        else:
            print("WARNING: Trend data is empty (all zeros).")

if __name__ == '__main__':
    verify_api()
