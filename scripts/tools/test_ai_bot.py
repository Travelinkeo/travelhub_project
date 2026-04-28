import os
import django
import sys

# Asegurar que el directorio raíz esté en el path para las importaciones
sys.path.append(os.getcwd())

# Configuramos el entorno de Django para poder usar sus modelos y Celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from apps.crm.tasks_bot import whatsapp_ai_task

def simular_mensaje_whatsapp():
    print("SIMULANDO MENSAJE DE WHATSAPP ENTRANTE...")
    print("--------------------------------------------------")
    
    telefono = "584129998877"
    cliente = "Elon Musk"
    mensaje = "Hola equipo de TravelHub! Necesito viajar urgente a Tokyo el proximo 25 de noviembre. Somos 4 personas en total (mi esposa, los 2 ninos y yo). Me pueden ayudar con la cotizacion?"
    
    print(f"CLIENTE: {cliente}")
    print(f"MENSAJE: {mensaje}")
    print("--------------------------------------------------")
    
    # Disparamos la tarea
    if len(sys.argv) > 1 and sys.argv[1] == '--sync':
        print("MODO SINCRO activado: Procesando directo en Gemini...")
        from apps.crm.services.whatsapp_bot_service import procesar_mensaje_entrante
        resultado = procesar_mensaje_entrante(telefono, cliente, mensaje)
        if resultado:
             from apps.crm.models_lead import OportunidadViaje
             print(f"EXITO: Lead procesado y guardado en DB. Total Leads: {OportunidadViaje.objects.count()}")
        else:
             print("FALLO: El procesamiento de Gemini no tuvo exito.")
    else:    
        # Carril 'ia_fast'
        whatsapp_ai_task.delay(telefono, cliente, mensaje)
        print("EXITO: Mensaje encolado en Celery.")
    
    print("--------------------------------------------------")
    print("Revisa tu terminal de Celery para ver el procesamiento.")
    print("Atento a tu Telegram para la notificacion.")
    print("Kanban: /crm/kanban/")

if __name__ == '__main__':
    simular_mensaje_whatsapp()
