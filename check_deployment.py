import requests
import time
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

def check_deployment():
    """Check if the Vercel deployment is working"""
    webhook_url = os.getenv('WEBHOOK_URL')
    if not webhook_url:
        print("❌ WEBHOOK_URL not found in environment")
        return False
    
    health_url = webhook_url.replace('/webhook', '/health')
    
    print(f"Checking deployment at: {health_url}")
    
    try:
        # Test health endpoint
        response = requests.get(health_url, timeout=10)
        print(f"Health check status: {response.status_code}")
        print(f"Health check response: {response.text}")
        
        if response.status_code == 200:
            print("✅ Health check successful!")
            return True
        else:
            print("❌ Health check failed!")
            return False
            
    except Exception as e:
        print(f"❌ Error checking deployment: {e}")
        return False

if __name__ == "__main__":
    print("Checking Vercel deployment status...")
    success = check_deployment()
    
    if success:
        print("\n✅ Deployment is working correctly!")
    else:
        print("\n❌ Deployment is not working yet. Please wait a moment and try again.")