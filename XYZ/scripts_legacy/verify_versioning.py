# verify_versioning.py
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.models import BoletoImportado, Agencia
from core.services.email_monitor_service import EmailMonitorService

def run():
    print("--- Iniciando Prueba de Versionado ---")
    
    # 1. Setup: Crear agencia de prueba y limpiar boletos previos
    agencia = Agencia.objects.first()
    if not agencia:
        print("Error: No hay agencia creada.")
        return

    BoletoImportado.objects.filter(numero_boleto='999-TEST-VERSION').delete()
    print("Limpieza realizada.")

    # 2. Mock de datos
    datos_ticket = {
        'SOURCE_SYSTEM': 'TEST',
        'numero_boleto': '999-TEST-VERSION',
        'SOLO_CODIGO_RESERVA': 'LOC123',
        'NOMBRE_DEL_PASAJERO': 'JUAN PEREZ',
        'NOMBRE_AEROLINEA': 'AEROLINEA TEST',
        'total': '100.00'
    }

    # 3. Instanciar servicio (mockeado parcialmente)
    service = EmailMonitorService(agencia=agencia)
    
    # 4. Primera Inserción (Versión 1)
    print("\nInsertando Versión 1...")
    # Llamamos a _guardar_y_notificar directamente para probar la lógica
    # Hack: Pasamos None como mail_connection y msg_num ya que no los usamos en esta parte
    result = service._guardar_y_notificar(datos_ticket, 1, mail_connection=None)
    
    boleto_v1 = BoletoImportado.objects.get(numero_boleto='999-TEST-VERSION', version=1)
    print(f"Versión 1 creada: ID={boleto_v1.id_boleto_importado}, Ver={boleto_v1.version}, Estado={boleto_v1.estado_emision}")
    assert boleto_v1.version == 1
    assert boleto_v1.estado_emision == BoletoImportado.EstadoEmision.ORIGINAL

    # 5. Segunda Inserción (Versión 2 - Re-emisión)
    print("\nInsertando Versión 2 (Simulando duplicado)...")
    result = service._guardar_y_notificar(datos_ticket, 2, mail_connection=None)
    
    boleto_v2 = BoletoImportado.objects.get(numero_boleto='999-TEST-VERSION', version=2)
    print(f"Versión 2 creada: ID={boleto_v2.id_boleto_importado}, Ver={boleto_v2.version}, Estado={boleto_v2.estado_emision}")
    print(f"Padre de V2: {boleto_v2.boleto_padre}")

    assert boleto_v2.version == 2
    assert boleto_v2.estado_emision == BoletoImportado.EstadoEmision.REEMISION
    assert boleto_v2.boleto_padre == boleto_v1
    
    print("\n--- PRUEBA EXITOSA: Versionado correcto ---")

if __name__ == '__main__':
    try:
        run()
    except Exception as e:
        print(f"FALLO: {e}")
