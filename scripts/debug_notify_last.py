
# scripts/debug_notify_last.py
import os
import sys
import django

# Setup Django
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.models import BoletoImportado
from django.conf import settings
from core.services.telegram_notification_service import TelegramNotificationService

def test_manual_notify():
    print("🔍 Buscando último boleto importado...")
    boleto = BoletoImportado.objects.order_by('-fecha_subida').first()
    
    if not boleto:
        print("❌ No hay boletos en la Base de Datos.")
        return

    print(f"🎫 Encontrado: Boleto ID {boleto.pk}")
    print(f"   Archivo: {boleto.archivo_boleto.name}")
    print(f"   PDF Generado: {boleto.archivo_pdf_generado.name if boleto.archivo_pdf_generado else 'NINGUNO'}")
    
    # 1. Verificar Configuración
    store_id = getattr(settings, 'TELEGRAM_STORAGE_CHANNEL_ID', 'NO_DEFINIDO')
    group_id = getattr(settings, 'TELEGRAM_GROUP_ID', 'NO_DEFINIDO')
    print(f"⚙️ Config: Storage={store_id}, Group={group_id}")
    
    # 2. Simular lógica de TicketParserService._generar_y_guardar_pdf (Parte Telegram)
    if not boleto.archivo_pdf_generado:
        print("⚠️ El boleto no tiene PDF generado. Intentando usar el archivo original como prueba...")
        pdf_file_input = boleto.archivo_boleto.path if hasattr(boleto.archivo_boleto, 'path') else None
    else:
        try:
             pdf_file_input = boleto.archivo_pdf_generado.path
             print(f"📂 Path detectado (FileSystem): {pdf_file_input}")
        except NotImplementedError:
             pdf_file_input = boleto.archivo_pdf_generado.url
             print(f"🌐 URL detectada (Cloud): {pdf_file_input}")
        except Exception as e:
             print(f"❌ Error obteniendo path: {e}")
             return

    caption = f"🧪 TEST MANUAL - Boleto {boleto.pk}\nPNR: {boleto.localizador_pnr}"

    # 3. Envío Manual A - STORAGE
    if store_id and store_id != 'NO_DEFINIDO':
        print(f"📤 Intentando envío a STORAGE ({store_id})...")
        try:
            res = TelegramNotificationService.send_document(
                file_path=pdf_file_input,
                caption=caption,
                chat_id=store_id
            )
            print(f"✅ Resultado Storage: {res}")
        except Exception as e:
            print(f"❌ Error Storage: {e}")

    # 4. Envío Manual B - GRUPO
    if group_id and group_id != 'NO_DEFINIDO':
        print(f"🔔 Intentando envío a GRUPO ({group_id})...")
        try:
            res = TelegramNotificationService.send_document(
                file_path=pdf_file_input,
                caption=caption,
                chat_id=group_id
            )
            print(f"✅ Resultado Grupo: {res}")
        except Exception as e:
            print(f"❌ Error Grupo: {e}")

if __name__ == "__main__":
    test_manual_notify()
