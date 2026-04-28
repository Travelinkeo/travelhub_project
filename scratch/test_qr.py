import requests
headers = {'X-Api-Key': '123456'}
try:
    r = requests.get('http://whatsapp_api:3000/api/default/auth/qr', headers=headers)
    print(f"QR Endpoint STATUS: {r.status_code}")
    print(f"ERROR DETAILS: {r.text}")
except Exception as e:
    print(f"ERROR: {e}")
