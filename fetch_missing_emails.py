
import os
import django
import imaplib
import email
from email.header import decode_header
import logging

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")
django.setup()

from django.conf import settings
from core.models import Agencia
from core.services.email_monitor_service import EmailMonitorService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fetch_specific_emails():
    # 1. Get Agency
    agencia = Agencia.objects.get(pk=1) # Travelinkeo
    
    if not agencia.email_monitor_user or not agencia.email_monitor_password:
        print("Error: No credentials for Agency 1")
        return

    print(f"Connecting to IMAP for {agencia.email_monitor_user}...")
    
    # 2. Connect IMAP
    mail = imaplib.IMAP4_SSL(settings.GMAIL_IMAP_HOST)
    try:
        mail.login(agencia.email_monitor_user, agencia.email_monitor_password)
    except Exception as e:
        print(f"Login failed: {e}")
        return

    mail.select('inbox')
    
    # 3. Search Criteria
    # We look for recent emails (last 30 days theoretically, but implicitly just latest by ID)
    # Search for FROM kiusys.com OR SUBJECT CONVIASA
    # Note: IMAP search is tricky with OR. We'll do two searches or fetch recent ALL and filter.
    # Safe bet: Search ALL, take last 50, filter manually.
    
    print("Searching for recent emails (Last 50)...")
    _, messages = mail.search(None, 'ALL')
    message_ids = messages[0].split()
    
    if not message_ids:
        print("No emails found.")
        return

    # Take last 50 IDs (most recent)
    recent_ids = message_ids[-50:]
    
    monitor = EmailMonitorService(agencia=agencia)
    processed_count = 0
    
    print(f"Scanning {len(recent_ids)} recent emails for Conviasa/KIU candidates...")
    
    for num in reversed(recent_ids): # Reverse to process newest first
        try:
            _, msg_data = mail.fetch(num, '(RFC822)')
            message = email.message_from_bytes(msg_data[0][1])
            
            subject = message.get('Subject', '')
            from_addr = message.get('From', '')
            
            # Decode subject
            decoded_header = decode_header(subject)
            subject_str = ""
            for part, charset in decoded_header:
                if isinstance(part, bytes):
                    subject_str += part.decode(charset or 'utf-8', errors='ignore')
                else:
                    subject_str += str(part)
            
            # Filter Criteria
            is_candidate = (
                'CONVIASA' in subject_str.upper() or 
                'KIUSYS' in from_addr.upper() or 
                'E-TICKET' in subject_str.upper() or
                'ELECTRONIC TICKET' in subject_str.upper() or
                'BOLETO' in subject_str.upper()
            )
            
            if is_candidate:
                print(f"Found Candidate: [{num.decode()}] {subject_str[:50]}... from {from_addr}")
                
                # Use the service logic to process it (extract and create BoletoImportado)
                # Note: This will download it to media/ and trigger parsing
                success = monitor._procesar_mensaje(message, num, mail)
                if success:
                    print(f"  -> SUCCESS: Processed and Saved.")
                    processed_count += 1
                else:
                    print(f"  -> SKIPPED: Monitor logic returned False (Maybe not a ticket or duplicates).")
            
        except Exception as e:
            print(f"Error checking email {num}: {e}")

    print(f"\nDone. Processed/Saved {processed_count} tickets.")
    mail.close()
    mail.logout()

if __name__ == '__main__':
    fetch_specific_emails()
