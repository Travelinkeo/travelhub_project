import requests
headers = {'X-Api-Key': '123456'}
try:
    r = requests.get('http://whatsapp_api:3000/api/sessions', headers=headers)
    print(f"STATUS: {r.status_code}")
    print(f"BODY: {r.text}")
except Exception as e:
    print(f"ERROR: {e}")
