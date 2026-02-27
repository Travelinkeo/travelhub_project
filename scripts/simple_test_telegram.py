import os
import requests
import sys

# Minimal script without Django overhead to test network/token
def test_simple_telegram():
    print("--- SIMPLE TELEGRAM TEST ---")
    
    # Load env vars manually to be sure
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except:
        pass

    token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHANNEL_ID') or os.getenv('TELEGRAM_GROUP_ID')
    
    # HARDCODED FALLBACK FOR DEBUGGING IF NEEDED (User to fill if env fails)
    # token = "..." 
    # chat_id = "..."
    
    if not token or not chat_id:
        print(f"❌ MISSING CONFIG: Token={bool(token)}, ChatID={chat_id}")
        return

    print(f"Token: {token[:5]}... | Chat: {chat_id}")
    
    url = f"https://api.telegram.org/bot{token}/sendDocument"
    print(f"URL: {url}")

    # Create dummy PDF
    filename = "simple_test.pdf"
    with open(filename, "wb") as f:
        f.write(b"Dummy PDF Content")

    try:
        with open(filename, 'rb') as f:
            files = {'document': f}
            data = {'chat_id': chat_id, 'caption': 'Simple Test 🚀'}
            
            print("Sending request (timeout=60s)...")
            response = requests.post(url, data=data, files=files, timeout=60)
            
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")

if __name__ == "__main__":
    test_simple_telegram()
