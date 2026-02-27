import os
import requests
import json
import time

def get_updates():
    # Load env vars manually
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except:
        pass

    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        print("❌ Error: No TELEGRAM_BOT_TOKEN found in .env")
        return

    print(f"🤖 Bot Token: {token[:5]}...")
    print("⏳ Waiting for updates... (Please post a message in the channel 'TravelHub DB' NOW)")
    
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    
    try:
        # Loop a few times to give user time
        for i in range(5):
            print(f"Requesting updates... (Attempt {i+1}/5)")
            response = requests.get(url, timeout=10)
            data = response.json()
            
            if not data.get('ok'):
                print(f"Error: {data}")
                break
                
            results = data.get('result', [])
            if not results:
                print("📭 No updates found yet...")
            else:
                found = False
                print("\n✅ Updates Found:")
                for update in results:
                    # Check channel_post or message
                    msg = update.get('channel_post') or update.get('message') or update.get('edited_message')
                    if msg:
                        chat = msg.get('chat', {})
                        chat_id = chat.get('id')
                        title = chat.get('title')
                        type_ = chat.get('type')
                        
                        print(f"📌 Chat: '{title}' (ID: {chat_id}) | Type: {type_}")
                        found = True
                
                if found:
                    print("\n✨ Identify the correct ID above!")
                    return
            
            time.sleep(3)
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    get_updates()
