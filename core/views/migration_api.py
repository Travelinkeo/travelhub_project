"""
API endpoints para validación de requisitos migratorios.
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from datetime import datetime

from core.models import Pasajero, Venta, MigrationCheck
from core.services.migration_checker_service import MigrationCheckerService


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def check_migration_requirements(request):
    """
    Endpoint para validar requisitos migratorios de un pasajero.
    
    POST /api/migration/check/
    
    Body:
    {
      "pasajero_id": 123,
      "vuelos": [
        {"origen": "CCS", "destino": "PTY", "fecha": "2026-03-15"},
        {"origen": "PTY", "destino": "MAD", "fecha": "2026-03-15"}
      ],
      "venta_id": 456  // opcional
    }
    
    Response:
    {
      "success": true,
      "check_id": 789,
      "alert_level": "YELLOW",
      "alert_emoji": "🟡",
      "summary": "Requiere visa de tránsito en Panamá",
      "details": {
        "visa_required": true,
        "visa_type": "Transit",
        "passport_validity_ok": true,
        "vaccination_required": [],
        "checked_by_ai": false
      }
    }
    """
    try:
        pasajero_id = request.data.get('pasajero_id')
        vuelos = request.data.get('vuelos', [])
        venta_id = request.data.get('venta_id')
        
        if not pasajero_id:
            return Response(
                {'error': 'pasajero_id es requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not vuelos:
            return Response(
                {'error': 'Debe proporcionar al menos un vuelo'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Convertir fechas de string a date
        for vuelo in vuelos:
            if isinstance(vuelo.get('fecha'), str):
                vuelo['fecha'] = datetime.strptime(vuelo['fecha'], '%Y-%m-%d').date()
        
        # Ejecutar validación
        service = MigrationCheckerService()
        check = service.check_migration_requirements(
            pasajero_id=pasajero_id,
            vuelos=vuelos,
            venta_id=venta_id,
            user=request.user
        )
        
        return Response({
            'success': True,
            'check_id': check.id,
            'alert_level': check.alert_level,
            'alert_emoji': check.get_alert_emoji(),
            'summary': check.summary,
            'details': {
                'visa_required': check.visa_required,
                'visa_type': check.visa_type,
                'passport_validity_ok': check.passport_validity_ok,
                'passport_min_months_required': check.passport_min_months_required,
                'vaccination_required': check.vaccination_required,
                'transit_countries': check.transitos,
                'checked_by_ai': check.checked_by_ai,
                'checked_at': check.checked_at.isoformat()
            }
        })
        
    except Pasajero.DoesNotExist:
        return Response(
            {'error': f'Pasajero {pasajero_id} no encontrado'},
            status=status.HTTP_404_NOT_FOUND
        )
    except ValueError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {'error': f'Error interno: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def quick_check_visa(request):
    """
    Validación rápida de requisitos de visa (sin guardar en BD).
    
    POST /api/migration/quick-check/
    
    Body:
    {
      "nationality": "VEN",
      "destination": "ESP"
    }
    
    Response:
    {
      "visa_required": false,
      "visa_type": "None - Espacio Schengen",
      "alert_level": "GREEN",
      "summary": "Máximo 90 días sin visa...",
      "passport_min_months": 3
    }
    """
    try:
        nationality = request.data.get('nationality', '').upper()
        destination = request.data.get('destination', '').upper()
        
        if not nationality or not destination:
            return Response(
                {'error': 'nationality y destination son requeridos'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        service = MigrationCheckerService()
        result = service.quick_check(nationality, destination)
        
        return Response({
            'visa_required': result.visa_required,
            'visa_type': result.visa_type,
            'passport_validity_ok': result.passport_validity_ok,
            'passport_min_months': result.passport_min_months,
            'vaccination_required': result.vaccination_required,
            'alert_level': result.alert_level,
            'summary': result.summary,
            'sources': result.sources
        })
        
    except Exception as e:
        return Response(
            {'error': f'Error: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_migration_checks(request, pasajero_id):
    """
    Obtiene el historial de validaciones de un pasajero.
    
    GET /api/migration/checks/<pasajero_id>/
    
    Response:
    {
      "pasajero": {...},
      "checks": [...]
    }
    """
    try:
        pasajero = get_object_or_404(Pasajero, id_pasajero=pasajero_id)
        checks = MigrationCheck.objects.filter(pasajero=pasajero).order_by('-checked_at')[:10]
        
        return Response({
            'pasajero': {
                'id': pasajero.id_pasajero,
                'nombre': pasajero.get_nombre_completo(),
                'nacionalidad': pasajero.nacionalidad.codigo_iso3 if pasajero.nacionalidad else None,
                'pasaporte_vence': pasajero.fecha_vencimiento_documento.isoformat() if pasajero.fecha_vencimiento_documento else None
            },
            'checks': [
                {
                    'id': check.id,
                    'destino': check.destino,
                    'transitos': check.transitos,
                    'alert_level': check.alert_level,
                    'alert_emoji': check.get_alert_emoji(),
                    'summary': check.summary,
                    'checked_at': check.checked_at.isoformat(),
                    'checked_by_ai': check.checked_by_ai
                }
                for check in checks
            ]
        })
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
