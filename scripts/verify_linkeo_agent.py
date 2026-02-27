import os
import sys
import django
from django.utils import timezone
import datetime
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.services.linkeo_agent_service import LinkeoAgentService
from core.models.ventas import Venta
from personas.models import Cliente
from core.models.agencia import Agencia
from django.contrib.auth.models import User
from core.models_catalogos import Moneda

import logging

# Configurar Logging
logging.basicConfig(level=logging.INFO)

# Check Key
key = os.getenv('GEMINI_API_KEY')
print(f"🔑 GEMINI_API_KEY status: {'LOADED' if key else 'MISSING'}")

def verify_linkeo():
    print("🧠 Verificando Linkeo Agent Service (Gemini AI)...")
    
    # 1. Setup Data
    user, _ = User.objects.get_or_create(username='linkeo_tester')
    agencia, _ = Agencia.objects.get_or_create(nombre="Agencia Linkeo Test", defaults={'propietario': user, 'email_principal': 'test@linkeo.com'})
    moneda, _ = Moneda.objects.get_or_create(codigo_iso='USD')
    
    # DEBUG: Imprimir campos del modelo
    print("Campos de Cliente:", [f.name for f in Cliente._meta.get_fields()])
    
    # Cliente Test - Usamos filter y create manual para aislar el error
    if not Cliente.objects.filter(nombres="Juan", apellidos="Perez").exists():
        print("Creando cliente manualmente...")
        cliente = Cliente()
        cliente.nombres = "Juan"
        cliente.apellidos = "Perez"
        cliente.cedula_identidad = 'V123456'
        cliente.telefono_principal = '+584121234567'
        # cliente.agencia = agencia  # Comentado para aislar error
        cliente.save()
        print(f"Cliente creado: {cliente}")
    else:
        cliente = Cliente.objects.filter(nombres="Juan", apellidos="Perez").first()
        print(f"Cliente encontrado: {cliente}")
    
    # Venta Test (Hoy)
    Venta.objects.create(
        cliente=cliente,
        agencia=agencia,
        creado_por=user,
        moneda=moneda,
        total_venta=500.00,
        fecha_venta=timezone.now()
    )
    
    # Mocking Gemini para probar lógica sin quota
    original_generate = LinkeoAgentService._detect_intent
    
    def mock_detect_intent(self, text):
        print(f"[MOCK] Detectando intento para: {text}")
        if "Juan" in text:
            return {"intent": "QUERY_CLIENT", "params": {"name_query": "Juan"}}
        elif "vendimos" in text:
             return {"intent": "QUERY_SALES", "params": {"date_range_start": timezone.now().date().isoformat()}}
        elif "visa" in text:
             return {"intent": "CHECK_MIGRATION", "params": {"nationality": "VEN", "destination": "ESP"}}
        return {"intent": "GENERAL", "params": {}}

    LinkeoAgentService._detect_intent = mock_detect_intent
    
    service = LinkeoAgentService()

    # 2. Test Cases
    test_queries = [
        "Hola Linkeo, ¿cómo estás?",
        "Busca al cliente Juan Perez",
        "¿Cuánto vendimos hoy?",
        "Necesito visa para ir a España siendo venezolano"
    ]
    
    for query in test_queries:
        print(f"\n🗣️ USUARIO: {query}")
        try:
            response = service.process_message(query)
            print(f"🤖 LINKEO: {response}")
        except Exception as e:
            print(f"❌ ERROR: {e}")

if __name__ == "__main__":
    verify_linkeo()
