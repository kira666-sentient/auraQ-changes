import os
import sys
import json
import urllib.request
import urllib.error
from dotenv import load_dotenv

# Explicitly load environment variables from .env file
load_dotenv()
print("Environment variables loaded from .env file")

def read_env_file():
    """Read the .env file and extract the GEMINI_API_KEY"""
    try:
        env_path = os.path.join(os.path.dirname(__file__), '.env')
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    if key == 'GEMINI_API_KEY':
                        return value
        return None
    except Exception as e:
        print(f"Error reading .env file: {str(e)}")
        return None

def check_gemini_api_key(api_key):
    """
    Validates the Gemini API key by making a simple test request to the Gemini API.
    Tests 3 different endpoints to ensure compatibility.
    """
    if not api_key:
        print("Error: GEMINI_API_KEY not found")
        return False
    
    # Try different model endpoints
    endpoints = [
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent",
        "https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent",
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.0-pro:generateContent"
    ]
    
    # Simple prompt for testing
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": "Hello, please respond with 'API key is valid' if you receive this message."
                    }
                ]
            }
        ]
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    data = json.dumps(payload).encode('utf-8')
    
    for endpoint in endpoints:
        print(f"\nTrying endpoint: {endpoint}")
        url = f"{endpoint}?key={api_key}"
        
        try:
            req = urllib.request.Request(url, data=data, headers=headers, method='POST')
            print(f"Sending request to: {url[:url.index('?key=') + 5]}[API_KEY_HIDDEN]")
            
            with urllib.request.urlopen(req) as response:
                if response.status == 200:
                    response_data = json.loads(response.read().decode('utf-8'))
                    print("✅ Your Gemini API key is valid!")
                    print("\nAPI Response:")
                    print(json.dumps(response_data, indent=2))
                    return True
                else:
                    print(f"❌ API key validation failed with status code: {response.status}")
                    
        except urllib.error.HTTPError as e:
            print(f"❌ API request failed with status code: {e.code}")
            error_content = e.read().decode('utf-8')
            try:
                error_json = json.loads(error_content)
                print(f"Error details: {error_json.get('error', {}).get('message', 'Unknown error')}")
            except:
                print(f"Error message: {error_content}")
            continue
        except Exception as e:
            print(f"❌ Error occurred while testing API key: {str(e)}")
            continue
    
    print("\nAll endpoints failed. Your API key may be invalid or the Gemini API endpoints might have changed.")
    return False

def verify_api_key(api_key):
    """
    Verify if the provided string looks like a valid Gemini API key
    """
    # Most Google API keys start with "AIza"
    if api_key and api_key.startswith("AIza"):
        print("✓ API key has the correct format (starts with AIza)")
        return True
    else:
        print("✗ API key doesn't have the expected Google API key format")
        print("  Valid Google API keys typically start with 'AIza'")
        return False

if __name__ == "__main__":
    print("Testing Gemini API key...")
    
    # First check environment variable
    env_api_key = os.environ.get("GEMINI_API_KEY")
    if env_api_key:
        print(f"Found API key in environment variables: {env_api_key[:5]}...{env_api_key[-5:]}")
        verify_api_key(env_api_key)
        check_gemini_api_key(env_api_key)
    else:
        print("No API key found in environment variables, checking .env file...")
        file_api_key = read_env_file()
        
        if file_api_key:
            print(f"Found API key in .env file: {file_api_key[:5]}...{file_api_key[-5:]}")
            verify_api_key(file_api_key)
            check_gemini_api_key(file_api_key)
        else:
            print("No API key found in .env file")
            print("\nEnvironment variables:")
            for key, value in os.environ.items():
                if "KEY" in key.upper() or "TOKEN" in key.upper() or "API" in key.upper():
                    print(f"{key}: {value[:3]}...{value[-3:] if len(value) > 6 else value}")