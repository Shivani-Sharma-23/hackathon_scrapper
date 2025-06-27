# debug_hackathon_api.py
import requests
import json

def test_hackathon_api():
    """Debug script to test hackathon API endpoints"""
    
    base_url = "https://hackathon-scrapper.onrender.com"
    
    print("=== HACKATHON API DEBUG SCRIPT ===\n")
    
    # Test 1: Health check
    print("1. Testing health endpoint...")
    try:
        response = requests.get(f"{base_url}/api/health", timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Health check failed: {e}")
    
    print("\n" + "="*50 + "\n")
    
    # Test 2: Test basic connection
    print("2. Testing basic connection...")
    try:
        response = requests.get(f"{base_url}/api/test", timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Test endpoint failed: {e}")
    
    print("\n" + "="*50 + "\n")
    
    # Test 3: Search hackathons (what your frontend is calling)
    print("3. Testing search hackathons endpoint...")
    try:
        params = {
            'q': '',
            'location': '',
            'mode': ''
        }
        response = requests.get(f"{base_url}/api/hackathons", params=params, timeout=15)
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response Data: {json.dumps(data, indent=2)}")
        else:
            print(f"Error Response: {response.text}")
            
    except Exception as e:
        print(f"Search hackathons failed: {e}")
    
    print("\n" + "="*50 + "\n")
    
    # Test 4: Try alternative search endpoint
    print("4. Testing alternative search endpoint...")
    try:
        response = requests.get(f"{base_url}/api/search-hackathons", timeout=15)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Hackathons found: {data.get('total', 0)}")
            if data.get('hackathons'):
                print(f"First hackathon: {data['hackathons'][0]}")
        else:
            print(f"Error Response: {response.text}")
            
    except Exception as e:
        print(f"Alternative search failed: {e}")

if __name__ == "__main__":
    test_hackathon_api()