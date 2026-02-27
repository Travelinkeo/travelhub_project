
import os
import django
import imaplib
import email
from email.header import decode_header

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from django.conf import settings
from core.models import Agencia

def debug_unread_emails():
    agencia = Agencia.objects.get(nombre="Travelinkeo")
    print(f"--- Debugging Inbox for: {agencia.email_monitor_user} ---")
    
    mail = imaplib.IMAP4_SSL('imap.gmail.com')
    try:
        mail.login(agencia.email_monitor_user, agencia.email_monitor_password)
    except Exception as e:
        print(f"Login failed: {e}")
        return

    mail.select('inbox')
    _, messages = mail.search(None, '(UNSEEN)')
    
    ids = messages[0].split()
    print(f"Found {len(ids)} UNSEEN messages.")
    
    for num in ids:
        # Use BODY.PEEK[] to avoid marking as read
        _, msg_data = mail.fetch(num, '(BODY.PEEK[])')
        msg = email.message_from_bytes(msg_data[0][1])
        
        subject = msg.get('Subject', '')
        from_addr = msg.get('From', '')
        
        # Decode subject
        decoded_list = decode_header(subject)
        subject_decoded = ''
        for t in decoded_list:
            content = t[0]
            charset = t[1]
            if isinstance(content, bytes):
                try:
                    subject_decoded += content.decode(charset or 'utf-8')
                except:
                    subject_decoded += content.decode('latin-1', errors='ignore')
            else:
                subject_decoded += str(content)
                
        print(f"\n[Msg ID: {int(num)}]")
        print(f"  From: {from_addr}")
        print(f"  Subject: {subject_decoded}")
        
        # Check Filters
        subject_upper = subject_decoded.upper()
        from_lower = from_addr.lower()
        
        is_kiu_subject = ('E-TICKET ITINERARY RECEIPT' in subject_upper or 
                         'ETICKET ITINERARY RECEIPT' in subject_upper or
                         'PASSENGER ITINERARY RECEIPT' in subject_upper)
                         
        is_kiu_sender = 'kiusys.com' in from_lower or 'travelinkeo@gmail.com' in from_lower
        
        print(f"  > Match KIU Subject? {is_kiu_subject}")
        print(f"  > Match KIU Sender? {is_kiu_sender}")
        
        # Check PDF
        tiene_pdf = False
        for part in msg.walk():
            if part.get_content_maintype() == 'multipart':
                continue
            if part.get('Content-Disposition') is None:
                continue
            filename = part.get_filename()
            if filename and filename.lower().endswith('.pdf'):
                tiene_pdf = True
        
        print(f"  > Has PDF? {tiene_pdf}")
        
        # DEBUG FULL STRUCTURE
        print("  [MIME STRUCTURE]")
        for part in msg.walk():
            print(f"    - Type: {part.get_content_type()}")
            
        # Try extraction logic manually
        txt = None
        html = None
        if msg.is_multipart():
             for part in msg.walk():
                 if part.get_content_type() == "text/plain":
                     txt = part.get_payload(decode=True)
                 if part.get_content_type() == "text/html":
                     html = part.get_payload(decode=True)
        else:
             if msg.get_content_type() == "text/plain":
                 txt = msg.get_payload(decode=True)
             elif msg.get_content_type() == "text/html":
                 html = msg.get_payload(decode=True)

        print(f"  [EXTRACTION TEST]")
        print(f"    - Text found? {bool(txt)} (Len: {len(txt) if txt else 0})")
        print(f"    - HTML found? {bool(html)} (Len: {len(html) if html else 0})")

        if is_kiu_subject or is_kiu_sender:
             print("  ✅ FILTERS PASSED (KIU)")
             if bool(txt) or bool(html):
                 print("  ✅ CONTENT FOUND -> SHOULD PROCESS")
             else:
                 print("  ❌ CONTENT MISSING -> WILL FAIL")
        elif tiene_pdf:
             print("  ✅ FILTERS PASSED (PDF)")
        else:
             print("  ❌ FILTERS FAILED")

    mail.close()
    mail.logout()

if __name__ == '__main__':
    debug_unread_emails()
