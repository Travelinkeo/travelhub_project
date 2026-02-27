
import os
import django
import json

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "travelhub.settings")
django.setup()

from core.models.boletos import BoletoImportado

def check_rutaca():
    # Buscar por parte del numero (sin guiones o con guiones)
    # User said: 765-0211263797
    ticket_num = "7650211263797"
    
    # Try exact match first
    boleto = BoletoImportado.objects.filter(numero_boleto__icontains="211263797").last()
    
    if not boleto:
        print("No se encontró el boleto en DB.")
        # List last 5
        print("Ultimos 5 boletos:")
        for b in BoletoImportado.objects.all().order_by('-fecha_subida')[:5]:
             print(f"- {b.numero_boleto} ({b.get_formato_detectado_display()})")
        return

    print(f"--- Datos del Boleto {boleto.numero_boleto} ---")
    print(f"ID: {boleto.pk}")
    print(f"Fecha Subida: {boleto.fecha_subida}")
    
    data = boleto.datos_parseados
    print(json.dumps(data, indent=2, ensure_ascii=False))
    
    # Check key specific fields
    print("\n--- Verificación de Campos Críticos ---")
    print(f"SOURCE_SYSTEM: {data.get('SOURCE_SYSTEM')}")
    print(f"AGENTE_EMISOR: {data.get('AGENTE_EMISOR')}")
    print(f"agente_emisor (lower): {data.get('agente_emisor')}")
    print(f"NOMBRE_AEROLINEA: {data.get('NOMBRE_AEROLINEA')}")
    print(f"aerolinea (lower): {data.get('aerolinea')}")
    print(f"DIRECCION_AEROLINEA: {data.get('DIRECCION_AEROLINEA')}")

if __name__ == "__main__":
    check_rutaca()
