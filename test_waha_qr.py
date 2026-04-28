import requests
import os

BASE_URL = "http://wppconnect:3000"
TOKEN = "THISISMYSECURETOKEN"
HEADERS = {"X-Api-Key": TOKEN}

def test():
    # 1. Get status
    r = requests.get(f"{BASE_URL}/api/sessions/", headers=HEADERS)
    print(f"Status: {r.text}")
    
    # 2. Try auth/qr
    r = requests.get(f"{BASE_URL}/api/default/auth/qr", headers=HEADERS)
    print(f"QR auth/qr status: {r.status_code}")
    
    # 3. Try screenshot
    r = requests.get(f"{BASE_URL}/api/screenshot?session=default", headers=HEADERS)
    print(f"Screenshot status: {r.status_code}")

if __name__ == "__main__":
    test()
