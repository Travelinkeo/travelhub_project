
import json

def test_kiu_context():
    # DATOS EXACTOS DEL USUARIO (Log Parseo)
    data = {
        "TOTAL": "VES 29988.14", 
        "TARIFA": "VES 21400.00", 
        "vuelos": [], 
        "IMPUESTOS": "375.096B 562.636S 5724.32AK 0.10C2 214.00EU 1712.00YN", 
        "TOTAL_MONEDA": "VES", 
        "AGENTE_EMISOR": "CCS00V0WV", 
        "SOURCE_SYSTEM": "KIU", 
        "TARIFA_MONEDA": "VES", 
        "TOTAL_IMPORTE": "29988.14", 
        "CODIGO_RESERVA": "C1/TXCGXK", 
        "TARIFA_IMPORTE": "21400.00", 
        "passenger_name": "CARLOS", 
        "FECHA_DE_EMISION": "04 FEB 2026 18:38", 
        "NOMBRE_AEROLINEA": "CONVIASA", 
        "NUMERO_DE_BOLETO": "308-0201387453", 
        "passenger_document": "NI84414910", 
        "DIRECCION_AEROLINEA": "AV. INTERCOMUNAL AEROPUERTO INTERNACIONAL DE MAIQUETIA EDO. LA GUAIRA VENEZUELA TELF +58 0500 266 8427", 
        "NOMBRE_DEL_PASAJERO": "CARLOS", 
        "SOLO_CODIGO_RESERVA": "TXCGXK", 
        "SOLO_NOMBRE_PASAJERO": "CARLOS", 
        "CODIGO_IDENTIFICACION": "NI84414910", 
        "ItinerarioFinalLimpio": "<B>CARACAS </B>V01186 O <B>11FEB 0700</B> <B>0800</B> OPROMO 23K OK\n<B> SAN ANTONIO </B>"
    }

    print(f"Data Inicial: {json.dumps(data, indent=2)}")

    # LOGICA DE core/ticket_parser.py
    agencia_data = data.get('agency', {})
    if not isinstance(agencia_data, dict): agencia_data = {}
    
    agente = agencia_data.get('nombre') or agencia_data.get('iata') or data.get('AGENTE_EMISOR') or data.get('agente_emisor', '')
    direccion_agencia = agencia_data.get('direccion') or data.get('DIRECCION_AEROLINEA') or data.get('direccion_aerolinea', '')

    context = {
        'boleto': {
            'pasajero_nombre_completo': data.get('passenger_name') or data.get('NOMBRE_DEL_PASAJERO', ''),
            'solo_nombre_pasajero': data.get('SOLO_NOMBRE_PASAJERO') or data.get('solo_nombre_pasajero', ''),
            'codigo_identificacion': data.get('passenger_document') or data.get('CODIGO_IDENTIFICACION') or 'PENDIENTE',
            'solo_codigo_reserva': data.get('pnr') or data.get('SOLO_CODIGO_RESERVA', ''),
            'numero_boleto': data.get('ticket_number') or data.get('NUMERO_DE_BOLETO', ''),
            'fecha_emision': data.get('issue_date') or data.get('FECHA_DE_EMISION', ''),
            'agente_emisor': agente,
            'aerolinea': data.get('airline_name') or data.get('NOMBRE_AEROLINEA', ''),
            'direccion_aerolinea': direccion_agencia,
            'vuelos': data.get('flights') or data.get('vuelos', []),
            'ruta': data.get('ItinerarioFinalLimpio') or data.get('ruta', '')
        }
    }

    print("\nContexto Generado:")
    print(json.dumps(context, indent=2))

    # VALIDACION
    boleto = context['boleto']
    missing = []
    if not boleto['fecha_emision']: missing.append('fecha_emision')
    if not boleto['agente_emisor']: missing.append('agente_emisor')
    if not boleto['direccion_aerolinea']: missing.append('direccion_aerolinea')

    if missing:
        print(f"\n❌ FALTAN CAMPOS: {missing}")
    else:
        print("\n✅ TODO CORRECTO")

if __name__ == "__main__":
    test_kiu_context()
