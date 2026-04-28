import requests
import json
import time

BASE_URL = "http://wppconnect:21465"
SECRET_KEY = "THISISMYSECURETOKEN"
SESSION = "TH_AGENCIA_1"

def test():
    print(f"--- Testing WPPConnect New Infrastructure ---")
    
    # 1. Generate Token
    token_url = f"{BASE_URL}/api/{SESSION}/{SECRET_KEY}/generate-token"
    print(f"Generating token: {token_url}")
    try:
        r = requests.post(token_url, timeout=10)
        print(f"Token Status: {r.status_code}")
        if r.status_code not in [200, 201]:
            print(f"Error: {r.text}")
            return
        token = r.json().get('token')
        print(f"Token generated: {token[:20]}...")
    except Exception as e:
        print(f"Connection Error: {e}")
        return

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # 2. Start Session
    start_url = f"{BASE_URL}/api/{SESSION}/start-session"
    print(f"Starting session: {start_url}")
    payload = {
        "waitQrCode": True,
        "createOptions": { "autoClose": 0 }
    }
    try:
        r = requests.post(start_url, json=payload, headers=headers, timeout=10)
        print(f"Start Status: {r.status_code}")
        print(f"Start Response: {r.text}")
    except Exception as e:
        print(f"Start Error (likely timeout, which is OK): {e}")

    # 3. Get Status
    status_url = f"{BASE_URL}/api/{SESSION}/status-session"
    print(f"Getting status: {status_url}")
    try:
        r = requests.get(status_url, headers=headers, timeout=10)
        print(f"Status Response: {r.text}")
    except Exception as e:
        print(f"Status Error: {e}")

    # 4. Get QR
    qr_url = f"{BASE_URL}/api/{SESSION}/qrcode-session"
    print(f"Getting QR: {qr_url}")
    try:
        r = requests.get(qr_url, headers=headers, timeout=10)
        print(f"QR Response Status: {r.status_code}")
        if r.status_code == 200:
            print("✅ QR Code found!")
            qr_data = r.json().get('qrcode')
            if qr_data:
                print(f"QR Prefix: {qr_data[:50]}...")
            else:
                print("QR data is EMPTY in the response!")
    except Exception as e:
        print(f"QR Error: {e}")
    # 5. Get Screenshot
    ss_url = f"{BASE_URL}/api/{SESSION}/screenshot"
    print(f"Getting Screenshot: {ss_url}")
    try:
        r = requests.get(ss_url, headers=headers, timeout=10)
        print(f"Screenshot Status: {r.status_code}")
        if r.status_code == 200:
            print("✅ Screenshot retrieved!")
            with open("/app/wpp_screenshot.png", "wb") as f:
                f.write(r.content)
            print("Screenshot saved to /app/wpp_screenshot.png")
    except Exception as e:
        print(f"Screenshot Error: {e}")

if __name__ == "__main__":
    test()
