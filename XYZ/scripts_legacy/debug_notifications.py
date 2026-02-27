import os
import django
import logging

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from django.conf import settings
from django.core.mail import EmailMessage
from core.utils.telegram_utils import send_telegram_alert_sync, send_telegram_file_sync

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_telegram():
    print("--- Testing Telegram ---")
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    admin_id = os.getenv('TELEGRAM_ADMIN_ID')
    group_id = os.getenv('TELEGRAM_GROUP_ID')
    
    print(f"Token present: {bool(token)}")
    print(f"Admin ID: {admin_id}")
    print(f"Group ID: {group_id}")
    
    msg = "🔔 Debug Test Message from TravelHub"
    print(f"Sending message: {msg}")
    result = send_telegram_alert_sync(msg)
    print(f"Message result: {result}")
    
    # Test file sending
    try:
        with open('debug_test.txt', 'w') as f:
            f.write("This is a test file for Telegram.")
        
        print("Sending test file...")
        result_file = send_telegram_file_sync('debug_test.txt', caption="Debug File")
        print(f"File result: {result_file}")
    except Exception as e:
        print(f"File sending error: {e}")

def test_email():
    print("\n--- Testing Email ---")
    dest = "viajes.travelinkeo@gmail.com"
    print(f"Sending email to: {dest}")
    print(f"From: {settings.EMAIL_HOST_USER}")
    
    try:
        email = EmailMessage(
            subject="Debug Test Email TravelHub",
            body="This is a test email to verify SMTP configuration.",
            from_email=settings.EMAIL_HOST_USER,
            to=[dest]
        )
        result = email.send()
        print(f"Email sent result: {result}")
    except Exception as e:
        print(f"Email error: {e}")

if __name__ == "__main__":
    test_telegram()
    test_email()
