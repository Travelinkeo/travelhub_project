import os
import django
import sys

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

import logging
from core.services.telegram_notification_service import TelegramNotificationService
from django.conf import settings

# Configure logging to console
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_send_pdf():
    print("--- STARTING TELEGRAM PDF TEST ---")
    
    token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_CHANNEL_ID
    
    print(f"Token present: {bool(token)}")
    print(f"Chat ID: {chat_id}")
    
    if not token or not chat_id:
        print("❌ MISSING CONFIGURATION")
        return

    # Create dummy PDF
    filename = "test_telegram.pdf"
    with open(filename, "wb") as f:
        f.write(b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/Resources <<\n/Font <<\n/F1 4 0 R\n>>\n>>\n/MediaBox [0 0 612 792]\n/Contents 5 0 R\n>>\nendobj\n4 0 obj\n<<\n/Type /Font\n/Subtype /Type1\n/Name /F1\n/BaseFont /Helvetica\n>>\nendobj\n5 0 obj\n<<\n/Length 44\n>>\nstream\nBT\n/F1 24 Tf\n100 100 Td\n(Hello Telegram World!) Tj\nET\nendstream\nendobj\nxref\n0 6\n0000000000 65535 f\n0000000010 00000 n\n0000000060 00000 n\n0000000157 00000 n\n0000000307 00000 n\n0000000396 00000 n\ntrailer\n<<\n/Size 6\n/Root 1 0 R\n>>\nstartxref\n492\n%%EOF")

    path = os.path.abspath(filename)
    print(f"Sending file: {path}")

    try:
        success = TelegramNotificationService.send_document(
            file_path=path,
            caption="🧪 Test PDF from Script",
            chat_id=chat_id
        )
        
        if success:
            print("✅ SUCCESS: PDF sent.")
        else:
            print("❌ FAILURE: Service returned False.")
            
    except Exception as e:
        print(f"❌ EXCEPTION: {e}")
    finally:
        if os.path.exists(path):
            os.remove(path)

if __name__ == "__main__":
    test_send_pdf()
