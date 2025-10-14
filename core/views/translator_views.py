# Archivo: core/views/translator_views.py

import logging
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse

from ..itinerary_translator import ItineraryTranslator, TicketCalculator
from ..models_catalogos import Aerolinea

logger = logging.getLogger(__name__)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@csrf_exempt
def translate_itinerary_api(request):
    """
    API para traducir itinerarios de diferentes GDS.
    
    POST /api/translator/itinerary/
    {
        "itinerary": "texto del itinerario",
        "gds_system": "SABRE|AMADEUS|KIU"
    }
    """
    try:
        itinerary = request.data.get('itinerary', '')
        gds_system = request.data.get('gds_system', 'SABRE')
        
        if not itinerary.strip():
            return Response(
                {'error': 'El itinerario no puede estar vacío'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        translator = ItineraryTranslator()
        translated = translator.translate_itinerary(itinerary, gds_system)
        
        return Response({
            'success': True,
            'translated_itinerary': translated,
            'gds_system': gds_system,
            'original_itinerary': itinerary
        })
        
    except Exception as e:
        logger.error(f"Error en translate_itinerary_api: {e}")
        return Response(
            {'error': 'Error interno del servidor'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@csrf_exempt
def calculate_ticket_price_api(request):
    """
    API para calcular precio de boletos.
    
    POST /api/translator/calculate/
    {
        "tarifa": 100.0,
        "fee_consolidador": 25.0,
        "fee_interno": 15.0,
        "porcentaje": 10.0
    }
    """
    try:
        tarifa = float(request.data.get('tarifa', 0))
        fee_consolidador = float(request.data.get('fee_consolidador', 0))
        fee_interno = float(request.data.get('fee_interno', 0))
        porcentaje = float(request.data.get('porcentaje', 0))
        
        if any(val < 0 for val in [tarifa, fee_consolidador, fee_interno, porcentaje]):
            return Response(
                {'error': 'Los valores no pueden ser negativos'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        result = TicketCalculator.calculate_ticket_price(
            tarifa, fee_consolidador, fee_interno, porcentaje
        )
        
        if 'error' in result:
            return Response(
                {'error': result['error']},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response({
            'success': True,
            'calculation': result
        })
        
    except (ValueError, TypeError) as e:
        return Response(
            {'error': 'Valores numéricos inválidos'},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Error en calculate_ticket_price_api: {e}")
        return Response(
            {'error': 'Error interno del servidor'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_supported_gds_api(request):
    """
    API para obtener los sistemas GDS soportados.
    
    GET /api/translator/gds/
    """
    try:
        supported_gds = [
            {
                'code': 'SABRE',
                'name': 'Sabre',
                'description': 'Sistema de reservas Sabre'
            },
            {
                'code': 'AMADEUS',
                'name': 'Amadeus',
                'description': 'Sistema de reservas Amadeus'
            },
            {
                'code': 'KIU',
                'name': 'KIU',
                'description': 'Sistema de reservas KIU'
            }
        ]
        
        return Response({
            'success': True,
            'supported_gds': supported_gds
        })
        
    except Exception as e:
        logger.error(f"Error en get_supported_gds_api: {e}")
        return Response(
            {'error': 'Error interno del servidor'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_airlines_catalog_api(request):
    """
    API para obtener el catálogo de aerolíneas.
    
    GET /api/translator/airlines/
    """
    try:
        airlines_list = []
        for airline in Aerolinea.objects.filter(activa=True, codigo_iata__isnull=False).exclude(codigo_iata=''):
            try:
                airlines_list.append({
                    'code': airline.codigo_iata,
                    'name': airline.nombre or 'Sin nombre',
                    'country': airline.pais.nombre if airline.pais else 'No especificado'
                })
            except Exception:
                # Skip airlines with data issues
                continue
        
        return Response({
            'success': True,
            'airlines': airlines_list,
            'total': len(airlines_list)
        })
        
    except Exception as e:
        logger.error(f"Error en get_airlines_catalog_api: {e}")
        return Response(
            {'error': 'Error interno del servidor'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_airports_catalog_api(request):
    """
    API para obtener el catálogo de aeropuertos.
    
    GET /api/translator/airports/
    """
    try:
        translator = ItineraryTranslator()
        airports = translator.airports
        
        airports_list = [
            {
                'code': code,
                'name': name
            }
            for code, name in airports.items()
        ]
        
        return Response({
            'success': True,
            'airports': airports_list,
            'total': len(airports_list)
        })
        
    except Exception as e:
        logger.error(f"Error en get_airports_catalog_api: {e}")
        return Response(
            {'error': 'Error interno del servidor'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@csrf_exempt
def validate_itinerary_format_api(request):
    """
    API para validar el formato de un itinerario sin traducirlo.
    
    POST /api/translator/validate/
    {
        "itinerary": "texto del itinerario",
        "gds_system": "SABRE|AMADEUS|KIU"
    }
    """
    try:
        itinerary = request.data.get('itinerary', '')
        gds_system = request.data.get('gds_system', 'SABRE')
        
        if not itinerary.strip():
            return Response(
                {'error': 'El itinerario no puede estar vacío'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validar formato básico
        lines = [line.strip() for line in itinerary.split('\n') if line.strip()]
        
        validation_result = {
            'is_valid': True,
            'total_lines': len(lines),
            'valid_lines': 0,
            'invalid_lines': [],
            'warnings': []
        }
        
        import re
        
        for i, line in enumerate(lines, 1):
            if gds_system.upper() == 'SABRE':
                # Patrón básico para SABRE
                pattern = r'^\s*\d+\s*[A-Z0-9]{2}\s*\d+\s*[A-Z]*\s+\d{2}[A-Z]{3}\s+\w\s+\w{3}\w{3}'
            elif gds_system.upper() == 'AMADEUS':
                # Patrón básico para AMADEUS
                pattern = r'^\s*\d+\s*[A-Z]{2}\s*\d+[A-Z]*\s+[A-Z]\s+[A-Z0-9]{5}\s+\w\s+\w{3}\w{3}'
            elif gds_system.upper() == 'KIU':
                # Patrón básico para KIU
                pattern = r'^\s*\d+\s+[A-Z0-9]{2}\s*\d+\s*[A-Z]*\s+\d{2}[A-Z]{3}\s+\w{2}\s+\w{3}\w{3}'
            else:
                return Response(
                    {'error': f'Sistema GDS no soportado: {gds_system}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if re.match(pattern, line):
                validation_result['valid_lines'] += 1
            else:
                validation_result['invalid_lines'].append({
                    'line_number': i,
                    'content': line,
                    'reason': f'No coincide con el formato esperado para {gds_system}'
                })
        
        # Determinar si es válido
        if validation_result['invalid_lines']:
            validation_result['is_valid'] = False
        
        # Agregar advertencias
        if validation_result['total_lines'] == 0:
            validation_result['warnings'].append('El itinerario está vacío')
        elif validation_result['valid_lines'] == 0:
            validation_result['warnings'].append('Ninguna línea tiene formato válido')
        elif validation_result['invalid_lines']:
            validation_result['warnings'].append(f'{len(validation_result["invalid_lines"])} líneas tienen formato incorrecto')
        
        return Response({
            'success': True,
            'gds_system': gds_system,
            'validation': validation_result
        })
        
    except Exception as e:
        logger.error(f"Error en validate_itinerary_format_api: {e}")
        return Response(
            {'error': 'Error interno del servidor'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@csrf_exempt
def batch_translate_api(request):
    """
    API para traducir múltiples itinerarios en lote.
    
    POST /api/translator/batch/
    {
        "itineraries": [
            {
                "id": "unique_id_1",
                "itinerary": "texto del itinerario 1",
                "gds_system": "SABRE"
            },
            {
                "id": "unique_id_2",
                "itinerary": "texto del itinerario 2",
                "gds_system": "AMADEUS"
            }
        ]
    }
    """
    try:
        itineraries = request.data.get('itineraries', [])
        
        if not itineraries or not isinstance(itineraries, list):
            return Response(
                {'error': 'Se requiere una lista de itinerarios'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if len(itineraries) > 10:  # Límite de seguridad
            return Response(
                {'error': 'Máximo 10 itinerarios por lote'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        translator = ItineraryTranslator()
        results = []
        
        for item in itineraries:
            item_id = item.get('id', f'item_{len(results) + 1}')
            itinerary = item.get('itinerary', '')
            gds_system = item.get('gds_system', 'SABRE')
            
            try:
                if not itinerary.strip():
                    results.append({
                        'id': item_id,
                        'success': False,
                        'error': 'Itinerario vacío',
                        'translated_itinerary': None
                    })
                    continue
                
                translated = translator.translate_itinerary(itinerary, gds_system)
                
                results.append({
                    'id': item_id,
                    'success': True,
                    'translated_itinerary': translated,
                    'gds_system': gds_system,
                    'original_itinerary': itinerary
                })
                
            except Exception as e:
                logger.error(f"Error procesando itinerario {item_id}: {e}")
                results.append({
                    'id': item_id,
                    'success': False,
                    'error': str(e),
                    'translated_itinerary': None
                })
        
        successful = sum(1 for r in results if r['success'])
        failed = len(results) - successful
        
        return Response({
            'success': True,
            'summary': {
                'total': len(results),
                'successful': successful,
                'failed': failed
            },
            'results': results
        })
        
    except Exception as e:
        logger.error(f"Error en batch_translate_api: {e}")
        return Response(
            {'error': 'Error interno del servidor'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )