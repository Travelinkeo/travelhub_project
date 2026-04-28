import os
import sys
import django
from django.core.files import File

# Setup Django
sys.path.append('c:/Users/ARMANDO/travelhub_project')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from apps.bookings.models import BoletoImportado, Venta
from core.services.ticket_parser_service import TicketParserService

def test_full_integration():
    print("🚀 Starting End-to-End Integration Test...")
    
    # 1. Pick a test file
    TEST_FILE_PATH = r"C:\Users\ARMANDO\Downloads\Boletos\7420200050864.pdf"
    
    if not os.path.exists(TEST_FILE_PATH):
        print(f"❌ Test file not found: {TEST_FILE_PATH}")
        return

    print(f"📂 Using file: {os.path.basename(TEST_FILE_PATH)}")

    # 2. Simulate Upload (Create BoletoImportado)
    with open(TEST_FILE_PATH, 'rb') as f:
        boleto = BoletoImportado()
        boleto.archivo_boleto.save(os.path.basename(TEST_FILE_PATH), File(f), save=True)
        boleto.estado_parseo = 'PEN'
        boleto.save()
        print(f"✅ Created BoletoImportado ID: {boleto.pk}")

    # 3. Process the Boleto (Triggers AI Router -> Extraction -> PDF)
    service = TicketParserService()
    print("🔄 Processing... (This calls AI Router)")
    
    try:
        resultado = service.procesar_boleto(boleto.pk)
    except Exception as e:
        print(f"❌ Processing Crashed: {e}")
        return

    # 4. Verify Results
    boleto.refresh_from_db()
    
    print("\n--- 🏁 Results ---")
    print(f"Status: {boleto.estado_parseo}")
    print(f"Log: {boleto.log_parseo}")
    
    if boleto.venta_asociada:
        print(f"✅ Venta Created: ID {boleto.venta_asociada.pk}")
        print(f"   Total: {boleto.venta_asociada.total_venta} {boleto.venta_asociada.moneda}")
    else:
        print("❌ Venta NOT Created")

    if boleto.archivo_pdf_generado:
        print(f"✅ PDF Generated: {boleto.archivo_pdf_generado.name}")
    else:
        print("❌ PDF NOT Generated")
        
    # Check if AI was used (look at logs or data)
    if boleto.datos_parseados:
        data = boleto.datos_parseados
        print(f"🧠 AI Router Data: {data.get('SOURCE_SYSTEM')} / {data.get('gds_detected')}")

if __name__ == "__main__":
    test_full_integration()
