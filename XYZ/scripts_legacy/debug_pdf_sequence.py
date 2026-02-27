import os
import django
import logging

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from django.conf import settings
from django.core.mail import EmailMessage
from core.utils.telegram_utils import send_telegram_file_sync
import time

# Configure logging
logging.basicConfig(level=logging.INFO)

def create_dummy_pdf(filename):
    # Minimal valid PDF content
    content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/Resources <<\n/Font <<\n/F1 4 0 R\n>>\n>>\n/MediaBox [0 0 612 792]\n/Contents 5 0 R\n>>\nendobj\n4 0 obj\n<<\n/Type /Font\n/Subtype /Type1\n/Name /F1\n/BaseFont /Helvetica\n>>\nendobj\n5 0 obj\n<<\n/Length 44\n>>\nstream\nBT\n/F1 24 Tf\n100 700 Td\n(Hello World from TravelHub Debug) Tj\nET\nendstream\nendobj\nxref\n0 6\n0000000000 65535 f\n0000000010 00000 n\n0000000060 00000 n\n0000000157 00000 n\n0000000307 00000 n\n0000000396 00000 n\ntrailer\n<<\n/Size 6\n/Root 1 0 R\n>>\nstartxref\n490\n%%EOF"
    
    with open(filename, 'wb') as f:
        f.write(content)
    return os.path.abspath(filename)

def test_sequence():
    filename = "debug_ticket.pdf"
    pdf_path = create_dummy_pdf(filename)
    print(f"Created dummy PDF at: {pdf_path}")

    # 1. Send via Telegram (Simulating _enviar_notificacion)
    print("\n[Step 1] Sending via Telegram...")
    try:
        success = send_telegram_file_sync(pdf_path, caption="Debug PDF Sequence Test")
        print(f"Telegram Result: {success}")
    except Exception as e:
        print(f"Telegram Failed: {e}")

    # 2. Send via Email (Simulating Backup Logic)
    print("\n[Step 2] Sending via Email (Backup)...")
    dest = "viajes.travelinkeo@gmail.com"
    try:
        email_msg = EmailMessage(
            subject='Debug Sequence Test - PDF Attachment',
            body='Testing sequential access to PDF file.',
            from_email=settings.EMAIL_HOST_USER,
            to=[dest]
        )
        
        # Read and attach
        with open(pdf_path, 'rb') as f:
            email_msg.attach(filename, f.read(), 'application/pdf')
        
        email_msg.send()
        print(f"Email Sent Successfully to {dest}")
    except Exception as e:
        print(f"Email Failed: {e}")

if __name__ == "__main__":
    test_sequence()
