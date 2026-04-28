import os
import sys
import django
import json
import datetime
import traceback

# Setup Django
sys.path.append('c:/Users/ARMANDO/travelhub_project')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from apps.automation.services.ai_router import GeminiRouter, EmailType

# PDF Extraction
try:
    import pypdf
except ImportError:
    try:
        import PyPDF2 as pypdf
    except ImportError:
        print("❌ pypdf or PyPDF2 not found. Install it: pip install pypdf")
        sys.exit(1)

# EML Extraction
try:
    import eml_parser
except ImportError:
    print("❌ eml_parser not found. Install it: pip install eml-parser")
    sys.exit(1)

USER_DOWNLOADS = r"C:\Users\ARMANDO\Downloads\Boletos"

def extract_text_from_pdf(path):
    text = ""
    try:
        reader = pypdf.PdfReader(path)
        for page in reader.pages:
            text += page.extract_text() + "\n"
    except Exception as e:
        print(f"⚠️ Error reading PDF {os.path.basename(path)}: {e}")
    return text

def extract_text_from_eml(path):
    text = ""
    try:
        with open(path, 'rb') as f:
            raw_email = f.read()
        ep = eml_parser.EmlParser()
        parsed_eml = ep.decode_email_bytes(raw_email)
        
        # Get body (simple logic, assuming plain text or html converted)
        # eml_parser returns a dict structure. body is usually in 'body' -> 'content'
        if 'body' in parsed_eml:
            for part in parsed_eml['body']:
                if 'content' in part:
                    text += part['content'] + "\n"
    except Exception as e:
        print(f"⚠️ Error reading EML {os.path.basename(path)}: {e}")
    return text

def process_file(router, file_path):
    ext = os.path.splitext(file_path)[1].lower()
    text = ""
    
    print(f"\n📂 Processing: {os.path.basename(file_path)}")
    
    if ext == '.pdf':
        text = extract_text_from_pdf(file_path)
    elif ext == '.eml':
        text = extract_text_from_eml(file_path)
    elif ext in ['.txt', '.html']:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()
        except:
            pass
    
    if not text.strip():
        print("   ❌ No text extracted (Scanned PDF? Encrypted?)")
        return

    print(f"   📝 Extracted {len(text)} chars.")
    
    # Classification
    try:
        category = router.classify_email(text[:5000]) # Send first 5k chars
        print(f"   🏷️ Classification: {category}")
        
        if category in [EmailType.TICKET_ISSUANCE, EmailType.SCHEDULE_CHANGE]:
            ticket = router.extract_ticket_data(text)
            if ticket:
                print(f"   ✅ Extraction SUCCESS:")
                print(f"      - PNR: {ticket.pnr}")
                print(f"      - Passenger: {ticket.passenger_name}")
                if ticket.total_amount:
                   print(f"      - Total: {ticket.total_amount} {ticket.currency}")
                if ticket.itinerary:
                   print(f"      - Itinerary: {len(ticket.itinerary)} segments")
                   for seg in ticket.itinerary:
                       print(f"        * {seg.airline_code}{seg.flight_number} {seg.origin}->{seg.destination} ({seg.departure_date})")
            else:
                print("   ❌ Extraction returned None")
    except Exception as e:
        print(f"   🔥 AI Error: {e}")

def main():
    print("🚀 Starting Batch Test on Real Tickets...")
    
    try:
        router = GeminiRouter()
    except Exception as e:
        print(f"❌ Router Init Failed: {e}")
        return

    count = 0
    MAX_FILES = 8 # Limit to avoid quota issues for demo
    
    for root, dirs, files in os.walk(USER_DOWNLOADS):
        for file in files:
            if file.lower().endswith(('.pdf', '.eml', '.txt', '.html')):
                if count >= MAX_FILES:
                    break
                full_path = os.path.join(root, file)
                process_file(router, full_path)
                count += 1
        if count >= MAX_FILES:
            break
            
    print("\n🏁 Batch Test Complete.")

if __name__ == "__main__":
    main()
