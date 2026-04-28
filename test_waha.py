import requests
import json
import time

BASE_URL = "http://wppconnect:3000"
SESSION = "default"

def test():
    print(f"--- Testing WAHA (Stable WPPConnect Wrapper) ---")
    
    # 1. Start Session
    start_url = f"{BASE_URL}/api/sessions/start"
    print(f"Starting session: {start_url}")
    payload = {
        "name": SESSION,
        "config": {
            "engine": "WEBJS",
            "browser": {
                "executablePath": "/usr/bin/chromium",
                "args": ["--no-sandbox"]
            }
        }
    }
    headers = {
        "X-Api-Key": "THISISMYSECURETOKEN",
        "Content-Type": "application/json"
    }
    try:
        r = requests.post(start_url, json=payload, headers=headers, timeout=30)
        print(f"Start Status: {r.status_code}")
        print(f"Start Response: {r.text}")
    except Exception as e:
        print(f"Start Error: {e}")

    # 2. Get Status
    status_url = f"{BASE_URL}/api/sessions/"
    print(f"Getting status: {status_url}")
    try:
        r = requests.get(status_url, headers=headers, timeout=10)
        print(f"Status Response: {r.text}")
    except Exception as e:
        print(f"Status Error: {e}")

    # 3. Get QR (Wait a bit for it to generate)
    print("Waiting 10s for QR generation...")
    time.sleep(10)
    qr_url = f"{BASE_URL}/api/{SESSION}/auth/qr"
    print(f"Getting QR: {qr_url}")
    try:
        r = requests.get(qr_url, headers=headers, timeout=10)
        print(f"QR Response Status: {r.status_code}")
        if r.status_code == 200:
            print("✅ QR Code (image) found!")
        else:
            print(f"QR Error: {r.text}")
    except Exception as e:
        print(f"QR Error: {e}")

if __name__ == "__main__":
    test()
