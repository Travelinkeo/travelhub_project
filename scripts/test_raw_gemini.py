import os
import requests
import json

# Manually read .env
api_key = None
try:
    with open('.env', 'r') as f:
        for line in f:
            if line.startswith('GEMINI_API_KEY='):
                api_key = line.strip().split('=')[1]
                break
except Exception as e:
    print(f"Error reading .env: {e}")

if not api_key:
    print("API Key not found in .env")
    exit(1)

url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"

print(f"Testing URL: {url.replace(api_key, 'HIDDEN_KEY')}")

try:
    response = requests.get(url) # GET request for list_models
    print(f"Status Code: {response.status_code}")
    print("Response Body:")
    print(response.text)
except Exception as e:
    print(f"Error: {e}")
