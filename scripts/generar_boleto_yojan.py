
import os
import django
import json
import re
from decimal import Decimal
from datetime import datetime

# --- Django Setup ---
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()
# --- End Django Setup ---

from django.db import transaction
from django.contrib.auth.models import User
from core.models import Venta, SegmentoVuelo
from core.models.facturacion import Moneda
from core.models_catalogos import Ciudad
from personas.models import Pasajero
from core.services.pdf_service import generar_pdf_voucher_unificado

# Datos para el nuevo pasajero
datos_boleto = {
  "reservation_code": "MSYHMI-2",
  "passenger_name": "YOJAN ARLEY BRAND ECHEVERRY",
  "document_number": "BE802929",
  "contact_email": "ventas1mydestiny@gmail.com", # Omitido en la plantilla, pero se mantiene por consistencia
  "total_paid": "514.47",
  "currency": "USD",
  "issuing_airline": "wingo",
  "flights": [
    {
      "type": "Vuelo de ida",
      "date": "Sun, 28 Sep",
      "departure_time": "08:43 AM",
      "departure_airport": "Caracas (CCS)",
      "arrival_time": "09:38 AM",
      "arrival_airport": "Bogotá (BOG)",
      "operated_by": "Aero República S.A"
    },
    {
      "type": "Vuelo de vuelta",
      "date": "Tue, 7 Oct",
      "departure_time": "04:54 AM",
      "departure_airport": "Bogotá (BOG)",
      "arrival_time": "07:52 AM",
      "arrival_airport": "Caracas (CCS)",
      "operated_by": "Aero República S.A"
    }
  ]
}

def parse_flight_datetime(date_str, time_str, year=2025):
    dt_format = f"{date_str} {year} {time_str}"
    return datetime.strptime(dt_format, "%a, %d %b %Y %I:%M %p")

def get_city_by_name(city_string):
    city_name_match = re.match(r'^(.*?)\s*\(', city_string)
    city_name = city_name_match.group(1).strip() if city_name_match else city_string
    
    try:
        print(f"Buscando Ciudad con nombre: '{city_name}'")
        return Ciudad.objects.get(nombre__iexact=city_name)
    except Ciudad.DoesNotExist:
        raise Exception(f"No se pudo encontrar una ciudad con el nombre '{city_name}' en la base de datos.")
    except Ciudad.MultipleObjectsReturned:
        if 'BOG' in city_string:
            return Ciudad.objects.get(nombre__iexact=city_name, pais__codigo_iso_2='CO')
        raise Exception(f"Se encontraron múltiples ciudades con el nombre '{city_name}'. Se necesita un criterio más específico.")

def run():
    print(f"Iniciando proceso para pasajero: {datos_boleto['passenger_name']}...")
    
    try:
        with transaction.atomic():
            creador = User.objects.filter(is_superuser=True).first()
            if not creador:
                raise Exception("No se encontró un superusuario.")

            moneda_usd, _ = Moneda.objects.get_or_create(codigo_iso='USD', defaults={'nombre': 'Dólar estadounidense', 'simbolo': '$'})

            nombre_completo = datos_boleto['passenger_name'].split()
            pasajero, _ = Pasajero.objects.get_or_create(
                numero_documento=datos_boleto['document_number'],
                defaults={'nombres': " ".join(nombre_completo[0:2]), 'apellidos': " ".join(nombre_completo[2:]), 'email': datos_boleto['contact_email']}
            )

            venta, created = Venta.objects.get_or_create(
                localizador=datos_boleto['reservation_code'],
                defaults={
                    'total_venta': Decimal(datos_boleto['total_paid']),
                    'moneda': moneda_usd,
                    'creado_por': creador,
                    'estado': 'CNF',
                    'descripcion_general': datos_boleto['issuing_airline']
                }
            )
            if created:
                print(f"Venta con localizador {venta.localizador} CREADA.")
            else:
                print(f"Venta con localizador {venta.localizador} ENCONTRADA.")

            venta.pasajeros.add(pasajero)

            for i, flight_data in enumerate(datos_boleto['flights']):
                fecha_salida = parse_flight_datetime(flight_data['date'], flight_data['departure_time'])
                
                ciudad_origen = get_city_by_name(flight_data['departure_airport'])
                ciudad_destino = get_city_by_name(flight_data['arrival_airport'])

                SegmentoVuelo.objects.get_or_create(
                    venta=venta,
                    fecha_salida=fecha_salida,
                    origen=ciudad_origen,
                    destino=ciudad_destino,
                    defaults={
                        'fecha_llegada': parse_flight_datetime(flight_data['date'], flight_data['arrival_time']),
                        'aerolinea': flight_data['operated_by'],
                    }
                )
                print(f"Segmento de vuelo {i+1} procesado.")
            
            print(f"Venta {venta.id_venta} lista en la base de datos.")

            print("Generando el PDF del voucher unificado...")
            pdf_bytes, filename = generar_pdf_voucher_unificado(venta_id=venta.id_venta)

            if pdf_bytes and filename:
                output_dir = 'media/boletos_generados'
                os.makedirs(output_dir, exist_ok=True)
                output_path = os.path.join(output_dir, filename)
                
                with open(output_path, 'wb') as f:
                    f.write(pdf_bytes)
                
                print("-" * 50)
                print("¡PROCESO COMPLETADO CON ÉXITO!")
                print(f"El PDF del voucher ha sido guardado en: {os.path.abspath(output_path)}")
                print("-" * 50)
            else:
                raise Exception("La función generar_pdf_voucher_unificado no devolvió un PDF.")

    except Exception as e:
        print(f"\n*** Ocurrió un error durante el proceso: {e} ***")

if __name__ == "__main__":
    run()
