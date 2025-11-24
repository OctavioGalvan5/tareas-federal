import requests

def test_login():
    url = 'http://127.0.0.1:5000/login'
    data = {
        'username': 'testadmin',
        'password': 'testpass123'
    }
    
    print(f"Attempting login to {url} with {data}...")
    
    try:
        # Use a session to persist cookies
        session = requests.Session()
        response = session.post(url, data=data, allow_redirects=True)
        
        print(f"Status Code: {response.status_code}")
        print(f"Final URL: {response.url}")
        
        if 'dashboard' in response.url:
            print("SUCCESS: Redirected to dashboard.")
        elif 'Usuario o contraseña incorrectos' in response.text:
            print("FAILURE: Invalid credentials message found.")
        else:
            print("UNKNOWN: Check output.")
            # print(response.text[:500]) # Print first 500 chars of response
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_login()
