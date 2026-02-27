
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
from core.models import Agencia, BoletoImportado
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
    
    # 3. Fetch recent emails (Last 150 to be safe)
    print("Searching for recent emails (Last 150)...")
    _, messages = mail.search(None, 'ALL')
    message_ids = messages[0].split()
    
    if not message_ids:
        print("No emails found.")
        return

    recent_ids = message_ids[-150:]
    
    monitor = EmailMonitorService(agencia=agencia)
    processed_count = 0
    target_pnr = 'WKTOTQ'
    target_name = 'ALEMAN'
    
    print(f"Scanning {len(recent_ids)} recent emails for {target_pnr} or {target_name}...")
    
    for num in reversed(recent_ids): # Reverse to process newest first
        try:
            _, msg_data = mail.fetch(num, '(RFC822)')
            message = email.message_from_bytes(msg_data[0][1])
            
            subject = message.get('Subject', '') or ''
            from_addr = message.get('From', '') or ''
            
            # Decode subject
            decoded_header = decode_header(subject)
            subject_str = ""
            for part, charset in decoded_header:
                if isinstance(part, bytes):
                    subject_str += part.decode(charset or 'utf-8', errors='ignore')
                else:
                    subject_str += str(part)
            
            # Extract plain text body for searching
            body_text = monitor._extraer_texto(message) or ""
            html_text = monitor._extraer_html(message) or ""
            full_content = (subject_str + " " + body_text + " " + html_text).upper()
            
            # Filter Criteria
            if target_pnr in full_content or target_name in full_content:
                print(f"Found Match! ID: {num.decode()} | Subj: {subject_str[:50]}...")
                
                # Check duplication first to avoid re-spamming if already processed
                # But user said they are missing, so we force re-process?
                # EmailMonitorService handles logging.
                
                success = monitor._procesar_mensaje(message, num, mail)
                if success:
                    print(f"  -> SUCCESS: Processed.")
                    processed_count += 1
                else:
                    print(f"  -> NO ACTION: Extractor returned False.")
            
        except Exception as e:
            print(f"Error checking email {num}: {e}")

    print(f"\nDone. Processed {processed_count} tickets.")
    mail.close()
    mail.logout()

if __name__ == '__main__':
    fetch_specific_emails()
