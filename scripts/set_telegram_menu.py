import os
import requests
import json

def set_menu_button():
    # Load env vars manually
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except:
        pass

    token = os.getenv('TELEGRAM_BOT_TOKEN')
    web_app_url = os.getenv('WEB_APP_URL')
    
    if not token:
        print("❌ Error: TELEGRAM_BOT_TOKEN missing.")
        return
        
    if not web_app_url:
        print("❌ Error: WEB_APP_URL missing in .env.")
        print("   Please add: WEB_APP_URL=https://your-app-url.com/flyer-generator")
        return

    print(f"🤖 Configuring Menu Button for Bot...")
    print(f"🔗 Web App URL: {web_app_url}")

    url = f"https://api.telegram.org/bot{token}/setChatMenuButton"
    
    payload = {
        "menu_button": {
            "type": "web_app",
            "text": "🎨 Crear Flyer",
            "web_app": {
                "url": web_app_url
            }
        }
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        data = response.json()
        
        if data.get('ok'):
            print("✅ SUCCESS: Menu Button configured!")
            print("   Restart your Telegram App to see the 'Crear Flyer' button.")
        else:
            print(f"❌ FAILED: {data}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    set_menu_button()
