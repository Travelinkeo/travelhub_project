import os
import django
from decimal import Decimal

# 1. Configurar Entorno
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.core.files import File
from apps.bookings.models import BoletoImportado, Venta
from core.services.ticket_parser_service import TicketParserService
from apps.crm.models_freelancer import FreelancerProfile, ComisionFreelancer
from core.middleware import _request_local

User = get_user_model()

def probar_comision_freelancer():
    print("🧪 Iniciando Prueba de Comisión Freelancer B2B2C...")
    
    # 2. Obtener Actor (Freelancer)
    try:
        usuario = User.objects.get(username='agente_freelancer')
        perfil = usuario.perfil_freelancer
        print(f"👤 Agente: {usuario.username} | Saldo Inicial: ${perfil.saldo_por_cobrar}")
    except Exception as e:
        print(f"❌ Error: El freelancer no está configurado. Ejecuta crear_freelancer.py primero. ({e})")
        return

    # 3. MOCK de Contexto de Petición (Thread-Local)
    # Esto simula que el freelancer está logueado en la web
    _request_local.meta = {'user': usuario, 'ip': '127.0.0.1'}
    _request_local.user = usuario
    
    # 4. Crear Boleto Importado de prueba
    estelar_path = r"C:\Users\ARMANDO\travelhub_project\core\tests\fixtures\venezuela_web\estelar_sample.eml"
    if not os.path.exists(estelar_path):
        print(f"❌ Error: No se encontró el archivo {estelar_path}")
        return

    with open(estelar_path, 'rb') as f:
        boleto = BoletoImportado.objects.create(
            archivo_boleto=File(f, name="estelar_test_freelancer.eml"),
            estado_parseo='PEN'
        )
    
    print(f"🎫 Boleto Creado (ID: {boleto.pk}). Procesando...")

    # 5. Ejecutar Parser (Invocará al interceptor)
    service = TicketParserService()
    resultado = service.procesar_boleto(boleto.pk)
    
    if resultado is None:
        print("❌ El parseo falló.")
        return

    # 6. VERIFICACIÓN FINAL
    perfil.refresh_from_db()
    comision = ComisionFreelancer.objects.filter(venta__localizador=boleto.localizador_pnr, freelancer=perfil).first()
    
    print("-" * 50)
    print(f"✅ ¡PROCESAMIENTO COMPLETADO!")
    print(f"✈️ PNR Extraído: {boleto.localizador_pnr}")
    print(f"👤 Pasajero: {boleto.nombre_pasajero_completo}")
    print(f"💰 Total Boleto: ${boleto.total_boleto}")
    
    if comision:
        print(f"🤑 COMISIÓN GENERADA: ${comision.monto_comision_ganada}")
        print(f"📈 NUEVO SALDO WALLET: ${perfil.saldo_por_cobrar}")
        if comision.monto_comision_ganada > 0:
            print("🚀 ÉXITO TOTAL: Los billetes están cayendo en la cuenta.")
        else:
             print("⚠️ Comisión asignada pero es $0 (Valida la utilidad de la venta).")
    else:
        print("❌ Error: No se generó registro de comisión. Revisa los logs de TicketParserService.")
    print("-" * 50)

if __name__ == '__main__':
    probar_comision_freelancer()
