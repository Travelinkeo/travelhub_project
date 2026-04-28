import os
import sys
import django

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.ticket_parser import extract_data_from_text, generate_ticket
import json

# Read the Copa ticket
file_path = r'C:\Users\ARMANDO\Downloads\Itinerary for Record Locator DYEXFG.eml'
with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

print("="*80)
print("COMPLETE END-TO-END COPA PARSER TEST")
print("="*80)

# Step 1: Check markers
print("\n📋 STEP 1: Checking Detection Markers")
print("-" * 80)
plain_upper = content.upper()

copa_markers = {
    'COPA AIRLINES': 'COPA AIRLINES' in plain_upper,
    'RECORD LOCATOR': 'RECORD LOCATOR' in plain_upper,
    'ACCELYA.COM': 'ACCELYA.COM' in plain_upper,
    'FARELOGIX.COM/SPRK': 'FARELOGIX.COM/SPRK' in plain_upper,
    'SPRK/PUBLIC/IMAGES': 'SPRK/PUBLIC/IMAGES' in plain_upper,
}

sabre_markers = {
    'ETICKET RECEIPT': 'ETICKET RECEIPT' in plain_upper,
    'RECIBO DE PASAJE ELECTRÓNICO': 'RECIBO DE PASAJE ELECTRÓNICO' in plain_upper,
    'RESERVATION CODE': 'RESERVATION CODE' in plain_upper,
    'CÓDIGO DE RESERVACIÓN': 'CÓDIGO DE RESERVACIÓN' in plain_upper,
}

print("\n🟢 Copa Markers:")
for marker, found in copa_markers.items():
    print(f"   {'✅' if found else '❌'} {marker}: {found}")

print("\n🔴 SABRE Markers:")
for marker, found in sabre_markers.items():
    print(f"   {'✅' if found else '❌'} {marker}: {found}")

# Step 2: Run parser
print("\n📋 STEP 2: Running Parser")
print("-" * 80)
try:
    result = extract_data_from_text(content, content)
    detected_system = result.get('SOURCE_SYSTEM', 'UNKNOWN')
    print(f"\n✅ Parser completed successfully!")
    print(f"🎯 Detected System: {detected_system}")
    
    if detected_system != 'COPA_SPRK':
        print(f"\n❌ ERROR: Expected 'COPA_SPRK' but got '{detected_system}'")
    else:
        print(f"\n✅ SUCCESS: Correctly detected as COPA_SPRK")
    
    print(f"\n📄 Extracted Data:")
    print(f"   PNR: {result.get('pnr', 'N/A')}")
    print(f"   Passenger: {result.get('pasajero', {}).get('nombre_completo', 'N/A')}")
    print(f"   Ticket Number: {result.get('numero_boleto', 'N/A')}")
    print(f"   Flights: {len(result.get('vuelos', []))} found")
    
except Exception as e:
    print(f"\n❌ Parser failed with error:")
    print(f"   {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    result = None

# Step 3: Generate PDF
if result and result.get('SOURCE_SYSTEM') == 'COPA_SPRK':
    print("\n📋 STEP 3: Generating PDF")
    print("-" * 80)
    try:
        pdf_bytes, filename = generate_ticket(result)
        
        if pdf_bytes:
            output_path = r'C:\Users\ARMANDO\travelhub_project\test_copa_output.pdf'
            with open(output_path, 'wb') as f:
                f.write(pdf_bytes)
            print(f"\n✅ PDF Generated Successfully!")
            print(f"   Output: {output_path}")
            print(f"   Size: {len(pdf_bytes)} bytes")
        else:
            print(f"\n❌ PDF generation returned empty bytes")
    except Exception as e:
        print(f"\n❌ PDF generation failed:")
        print(f"   {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
else:
    print("\n⚠️ Skipping PDF generation (parser failed or wrong system detected)")

print("\n" + "="*80)
print("TEST COMPLETE")
print("="*80)
