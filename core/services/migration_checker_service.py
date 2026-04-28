"""
Servicio principal para validación de requisitos migratorios.

Este servicio orquesta la validación de requisitos de visa, validez de pasaporte
y vacunas requeridas, usando una combinación de:
1. Cache Redis (para respuestas rápidas)
2. Base de datos local de reglas comunes
3. Gemini AI (para casos complejos o actualizaciones)
"""
import logging
from datetime import date, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict

from django.core.cache import cache
from django.utils import timezone

from core.models import MigrationCheck
from apps.bookings.models import Venta
from apps.crm.models import Pasajero
from .gemini_migration_validator import GeminiMigrationValidator, MigrationValidationResult

logger = logging.getLogger(__name__)


# Base de datos local de reglas comunes (hardcoded para inicio)
MIGRATION_RULES_DB = {
    # Formato: (nationality, destination): {reglas}
    ('VEN', 'ESP'): {
        'visa_required': False,
        'visa_type': 'None - Espacio Schengen',
        'passport_min_months': 3,
        'notes': 'Máximo 90 días sin visa. Pasaporte válido 3 meses después del retorno.'
    },
    ('VEN', 'USA'): {
        'visa_required': True,
        'visa_type': 'B1/B2 Tourist',
        'passport_min_months': 6,
        'notes': 'Visa de turista requerida. Pasaporte debe tener 6 meses de validez.'
    },
    ('VEN', 'PAN'): {
        'visa_required': False,
        'visa_type': 'None',
        'passport_min_months': 6,
        'notes': 'No requiere visa para turismo (hasta 90 días).'
    },
    ('VEN', 'MEX'): {
        'visa_required': False,
        'visa_type': 'None',
        'passport_min_months': 6,
        'notes': 'No requiere visa. Llenar FMM (Forma Migratoria Múltiple).'
    },
    ('VEN', 'BRA'): {
        'visa_required': False,
        'visa_type': 'None',
        'passport_min_months': 6,
        'vaccination_required': ['Yellow Fever'],
        'notes': 'No requiere visa (MERCOSUR). Vacuna fiebre amarilla obligatoria.'
    },
    ('COL', 'ESP'): {
        'visa_required': False,
        'visa_type': 'None - Espacio Schengen',
        'passport_min_months': 3,
        'notes': 'Máximo 90 días sin visa.'
    },
    ('COL', 'USA'): {
        'visa_required': True,
        'visa_type': 'B1/B2 Tourist',
        'passport_min_months': 6,
        'notes': 'Visa de turista requerida.'
    },
}


class MigrationCheckerService:
    """
    Servicio principal para validación de requisitos migratorios.
    """
    
    def __init__(self):
        """Inicializa el servicio con el validador de Gemini"""
        self.gemini_validator = GeminiMigrationValidator()
        self.cache_ttl = 60 * 60 * 24 * 7  # 7 días en segundos
    
    def check_migration_requirements(
        self,
        pasajero_id: int,
        vuelos: List[Dict[str, Any]],
        venta_id: Optional[int] = None,
        user=None
    ) -> MigrationCheck:
        """
        Valida requisitos migratorios para un pasajero y sus vuelos.
        
        Args:
            pasajero_id: ID del pasajero a validar
            vuelos: Lista de diccionarios con info de vuelos [{'origen': 'CCS', 'destino': 'MAD', 'fecha': date}]
            venta_id: ID de la venta asociada (opcional)
            user: Usuario que solicita la validación (opcional)
        
        Returns:
            MigrationCheck: Objeto con el resultado de la validación
        """
        try:
            pasajero = Pasajero.objects.get(id_pasajero=pasajero_id)
        except Pasajero.DoesNotExist:
            raise ValueError(f"Pasajero {pasajero_id} no encontrado")
        
        if not vuelos:
            raise ValueError("Debe proporcionar al menos un vuelo")
        
        # Extraer datos del viaje
        origen = vuelos[0].get('origen')
        destino = vuelos[-1].get('destino')  # Destino final
        fecha_viaje = vuelos[0].get('fecha')
        
        # Extraer tránsitos (aeropuertos intermedios)
        transitos = []
        if len(vuelos) > 1:
            transitos = [v.get('destino') for v in vuelos[:-1]]
        
        # Obtener nacionalidad del pasajero
        nationality_code = self._get_nationality_code(pasajero)
        
        # Validar pasaporte
        passport_validity_ok, passport_months = self._check_passport_validity(
            pasajero.fecha_vencimiento_documento,
            fecha_viaje
        )
        
        # Intentar obtener de cache
        cache_key = self._build_cache_key(nationality_code, destino, transitos)
        cached_result = cache.get(cache_key)
        
        if cached_result:
            logger.info(f"✅ Usando resultado en cache para {nationality_code} → {destino}")
            validation_result = MigrationValidationResult(**cached_result)
            used_ai = False
        else:
            # Intentar obtener de reglas locales
            local_rule = MIGRATION_RULES_DB.get((nationality_code, destino))
            
            if local_rule and not transitos:
                logger.info(f"📚 Usando regla local para {nationality_code} → {destino}")
                validation_result = self._build_result_from_local_rule(local_rule, passport_validity_ok)
                used_ai = False
            else:
                # Consultar Gemini AI
                logger.info(f"🤖 Consultando Gemini AI para {nationality_code} → {destino}")
                validation_result = self.gemini_validator.validate_visa_requirements(
                    nationality=nationality_code,
                    destination=destino,
                    transit_countries=transitos,
                    passport_expiry=pasajero.fecha_vencimiento_documento,
                    travel_date=fecha_viaje
                )
                used_ai = True
            
            # Guardar en cache
            cache.set(cache_key, asdict(validation_result), self.cache_ttl)
        
        # Ajustar nivel de alerta según validez de pasaporte
        alert_level = validation_result.alert_level
        if not passport_validity_ok:
            alert_level = 'RED'
            validation_result.summary = f"⚠️ PASAPORTE INSUFICIENTE ({passport_months} meses). " + validation_result.summary
        
        # Verificar vacunas
        if 'Yellow Fever' in validation_result.vaccination_required:
            if not pasajero.tiene_fiebre_amarilla:
                alert_level = 'YELLOW' if alert_level == 'GREEN' else alert_level
                validation_result.summary += " | ⚠️ Requiere vacuna fiebre amarilla."
        
        # Crear registro en base de datos
        migration_check = MigrationCheck.objects.create(
            pasajero=pasajero,
            venta_id=venta_id,
            origen=origen,
            destino=destino,
            transitos=transitos,
            fecha_viaje=fecha_viaje,
            alert_level=alert_level,
            visa_required=validation_result.visa_required,
            visa_type=validation_result.visa_type,
            passport_validity_ok=passport_validity_ok,
            passport_min_months_required=validation_result.passport_min_months,
            vaccination_required=validation_result.vaccination_required,
            summary=validation_result.summary,
            full_report=asdict(validation_result),
            checked_by_ai=used_ai,
            checked_by_user=user
        )
        
        logger.info(f"{migration_check.get_alert_emoji()} Validación completada: {pasajero.get_nombre_completo()} → {destino}")
        
        return migration_check
    
    def quick_check(self, nationality: str, destination: str) -> MigrationValidationResult:
        """
        Validación rápida sin guardar en BD (para comando Telegram).
        
        Args:
            nationality: Código ISO de nacionalidad (ej: 'VEN')
            destination: Código ISO de destino (ej: 'ESP')
        
        Returns:
            MigrationValidationResult
        """
        cache_key = self._build_cache_key(nationality, destination, [])
        cached_result = cache.get(cache_key)
        
        if cached_result:
            return MigrationValidationResult(**cached_result)
        
        # Intentar regla local
        local_rule = MIGRATION_RULES_DB.get((nationality, destination))
        if local_rule:
            result = self._build_result_from_local_rule(local_rule, True)
        else:
            # Consultar Gemini
            result = self.gemini_validator.validate_visa_requirements(
                nationality=nationality,
                destination=destination
            )
        
        cache.set(cache_key, asdict(result), self.cache_ttl)
        return result
    
    def _get_nationality_code(self, pasajero: Pasajero) -> str:
        """Extrae el código ISO de nacionalidad del pasajero"""
        if pasajero.nacionalidad:
            # Asumiendo que el modelo Pais tiene un campo 'codigo_iso3'
            return getattr(pasajero.nacionalidad, 'codigo_iso3', 'VEN')
        return 'VEN'  # Default
    
    def _check_passport_validity(
        self,
        passport_expiry: Optional[date],
        travel_date: Optional[date],
        min_months: int = 6
    ) -> tuple[bool, int]:
        """
        Verifica si el pasaporte tiene validez suficiente.
        
        Args:
            passport_expiry: Fecha de vencimiento del pasaporte
            travel_date: Fecha del viaje
            min_months: Meses mínimos requeridos (default: 6)
        
        Returns:
            (is_valid, months_remaining)
        """
        if not passport_expiry:
            return False, 0
        
        if not travel_date:
            travel_date = date.today()
        
        # Calcular meses de validez
        months_valid = (passport_expiry.year - travel_date.year) * 12 + \
                      (passport_expiry.month - travel_date.month)
        
        is_valid = months_valid >= min_months
        
        return is_valid, months_valid
    
    def _build_cache_key(self, nationality: str, destination: str, transits: List[str]) -> str:
        """Construye la clave de cache"""
        transit_str = "-".join(sorted(transits)) if transits else "direct"
        return f"migration:{nationality}:{destination}:{transit_str}"
    
    def _build_result_from_local_rule(
        self,
        rule: Dict[str, Any],
        passport_ok: bool
    ) -> MigrationValidationResult:
        """Construye un MigrationValidationResult desde una regla local"""
        
        # Determinar nivel de alerta
        if not passport_ok:
            alert_level = 'RED'
        elif rule.get('visa_required'):
            alert_level = 'YELLOW'
        else:
            alert_level = 'GREEN'
        
        return MigrationValidationResult(
            visa_required=rule.get('visa_required', False),
            visa_type=rule.get('visa_type', 'None'),
            passport_validity_ok=passport_ok,
            passport_min_months=rule.get('passport_min_months', 6),
            vaccination_required=rule.get('vaccination_required', []),
            alert_level=alert_level,
            summary=rule.get('notes', 'Verificar requisitos actualizados'),
            sources=['Base de datos local TravelHub']
        )
