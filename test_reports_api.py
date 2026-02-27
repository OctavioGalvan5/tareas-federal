import requests
import json
from datetime import datetime, timedelta

# Configurar fechas
end_date = datetime.now()
start_date = end_date - timedelta(days=30)

# Datos a enviar
payload = {
    'user_ids': [],
    'tag_ids': [],
    'status': 'All',
    'area': 'all',
    'start_date': start_date.strftime('%Y-%m-%d'),
    'end_date': end_date.strftime('%Y-%m-%d')
}

print("Testing /api/reports/data endpoint...")
print(f"Payload: {json.dumps(payload, indent=2)}")
print()

try:
    response = requests.post(
        'http://127.0.0.1:5000/api/reports/data',
        json=payload,
        headers={'Content-Type': 'application/json'}
    )

    print(f"Status Code: {response.status_code}")
    print()

    if response.status_code == 200:
        data = response.json()
        print("Response data:")
        print(json.dumps(data, indent=2))
    else:
        print(f"Error: {response.text}")

except Exception as e:
    print(f"Exception: {e}")
