import requests
import json

# Probar el endpoint de login directamente
url = "http://localhost:8000/api/auth/login/"
data = {
    "username": "Armando3105",
    "password": "Linkeo1331*"
}

print("Probando login...")
print(f"URL: {url}")
print(f"Data: {data}")

try:
    response = requests.post(url, json=data)
    print(f"Status Code: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")
    print(f"Response: {response.text[:500]}...")
except Exception as e:
    print(f"Error: {e}")