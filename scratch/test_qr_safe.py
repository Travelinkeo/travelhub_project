import requests
headers = {'X-Api-Key': '123456'}
try:
    r = requests.get('http://whatsapp_api:3000/api/default/auth/qr', headers=headers)
    print(f"STATUS: {r.status_code}")
    print(f"CONTENT-TYPE: {r.headers.get('Content-Type')}")
    print(f"LENGTH: {len(r.content)}")
    if r.status_code != 200:
        print(f"ERROR: {r.text}")
except Exception as e:
    print(f"ERROR: {e}")
