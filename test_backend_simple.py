import requests
import json

def test_backend():
    try:
        # Test health endpoint
        response = requests.get("http://localhost:8000/health")
        print(f"Health check: {response.status_code} - {response.json()}")
        
        # Test market status endpoint
        response = requests.get("http://localhost:8000/api/v1/market/status")
        print(f"Market status: {response.status_code} - {response.json()}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_backend()
