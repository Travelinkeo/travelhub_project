
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from apps.finance.services.accounting_assistant import AccountingAssistantService
from core.models import Agencia

def test_assistant():
    print("--- Iniciando Prueba de Asistente Contable AI ---")
    
    agencia = Agencia.objects.filter(nombre="Agencia AI Test").first()
    if not agencia:
        print("ERROR: No se encontro la agencia de prueba Agencia AI Test.")
        return

    assistant = AccountingAssistantService(agencia)
    
    # Prueba 1: Preguntar por un boleto con discrepancia
    print("\nUSER: ¿Por qué el boleto 1230000000002 tiene una diferencia?")
    response = assistant.ask("Explicame por que el boleto 1230000000002 tiene una diferencia financiera.")
    print(f"ASSISTANT: {response}")

    # Prueba 2: Proponer ajuste
    print("\nUSER: ¿Qué asiento contable me sugieres para arreglar esta diferencia?")
    response = assistant.ask("Dime que asiento contable (Debe/Haber) me sugieres para arreglar la diferencia de 5.5 del boleto 1230000000002.")
    print(f"ASSISTANT: {response}")

    # Prueba 3: Listar fallos generales

if __name__ == "__main__":
    test_assistant()
