"""
Cliente especializado para validaciones migratorias usando Gemini AI.
"""
import logging
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import date

# import google.generativeai as genai
from django.conf import settings

logger = logging.getLogger(__name__)


@dataclass
class MigrationValidationResult:
    """Resultado estructurado de una validación migratoria"""
    visa_required: bool
    visa_type: str
    passport_validity_ok: bool
    passport_min_months: int
    vaccination_required: list
    alert_level: str  # RED, YELLOW, GREEN
    summary: str
    sources: list
    raw_response: str = ""


class GeminiMigrationValidator:
    """
    Cliente para consultas de requisitos migratorios usando Gemini AI.
    
    Este servicio construye prompts especializados y parsea las respuestas
    de Gemini para extraer información sobre visas, validez de pasaportes
    y requisitos de vacunación.
    """
    
    def __init__(self):
        """Inicializa el cliente de Gemini"""
        api_key = settings.GEMINI_API_KEY
        if not api_key:
            raise ValueError("GEMINI_API_KEY no configurada en settings")
        
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
    
    def validate_visa_requirements(
        self,
        nationality: str,
        destination: str,
        transit_countries: list = None,
        passport_expiry: date = None,
        travel_date: date = None
    ) -> MigrationValidationResult:
        """
        Valida requisitos migratorios usando Gemini AI.
        
        Args:
            nationality: Código ISO del país de nacionalidad (ej: 'VEN', 'COL')
            destination: Código ISO del país de destino (ej: 'ESP', 'USA')
            transit_countries: Lista de códigos ISO de países de tránsito
            passport_expiry: Fecha de vencimiento del pasaporte
            travel_date: Fecha del viaje
        
        Returns:
            MigrationValidationResult con los requisitos detectados
        """
        try:
            prompt = self._build_migration_prompt(
                nationality=nationality,
                destination=destination,
                transit_countries=transit_countries or [],
                passport_expiry=passport_expiry,
                travel_date=travel_date
            )
            
            logger.info(f"🤖 Consultando Gemini: {nationality} → {destination}")
            
            response = self.model.generate_content(prompt)
            raw_text = response.text
            
            logger.debug(f"Respuesta Gemini: {raw_text[:200]}...")
            
            # Parsear respuesta
            result = self._parse_gemini_response(raw_text)
            result.raw_response = raw_text
            
            return result
            
        except Exception as e:
            logger.error(f"Error consultando Gemini: {e}")
            # Retornar resultado conservador en caso de error
            return MigrationValidationResult(
                visa_required=True,  # Asumir que sí requiere visa por seguridad
                visa_type="Unknown - Verify with Embassy",
                passport_validity_ok=False,
                passport_min_months=6,
                vaccination_required=[],
                alert_level="YELLOW",
                summary=f"No se pudo validar automáticamente. Verificar con embajada de {destination}.",
                sources=[],
                raw_response=str(e)
            )
    
    def _build_migration_prompt(
        self,
        nationality: str,
        destination: str,
        transit_countries: list,
        passport_expiry: Optional[date],
        travel_date: Optional[date]
    ) -> str:
        """Construye el prompt optimizado para Gemini"""
        
        # Mapeo de códigos a nombres de países (simplificado)
        country_names = {
            'VEN': 'Venezuela', 'COL': 'Colombia', 'ARG': 'Argentina',
            'ESP': 'España', 'USA': 'Estados Unidos', 'PAN': 'Panamá',
            'MEX': 'México', 'BRA': 'Brasil', 'PER': 'Perú',
            'CHL': 'Chile', 'ECU': 'Ecuador', 'URY': 'Uruguay',
            'PRY': 'Paraguay', 'BOL': 'Bolivia', 'CRI': 'Costa Rica',
            'DOM': 'República Dominicana', 'CUB': 'Cuba', 'JAM': 'Jamaica',
            'FRA': 'Francia', 'ITA': 'Italia', 'DEU': 'Alemania',
            'GBR': 'Reino Unido', 'PRT': 'Portugal', 'NLD': 'Países Bajos',
            'CAN': 'Canadá', 'AUS': 'Australia', 'JPN': 'Japón',
            'CHN': 'China', 'IND': 'India', 'RUS': 'Rusia'
        }
        
        nationality_name = country_names.get(nationality, nationality)
        destination_name = country_names.get(destination, destination)
        transit_names = [country_names.get(c, c) for c in transit_countries]
        
        # Calcular meses de validez del pasaporte
        passport_info = ""
        if passport_expiry and travel_date:
            months_valid = (passport_expiry.year - travel_date.year) * 12 + (passport_expiry.month - travel_date.month)
            passport_info = f"- Pasaporte válido hasta: {passport_expiry.strftime('%Y-%m-%d')} ({months_valid} meses desde la fecha de viaje)\n"
        
        transit_info = ""
        if transit_names:
            transit_info = f"- Escalas/Tránsitos: {', '.join(transit_names)}\n"
        
        prompt = f"""Eres un experto en regulaciones migratorias internacionales actualizadas a 2026.

DATOS DEL VIAJE:
- Nacionalidad del pasajero: {nationality_name} ({nationality})
{passport_info}- Origen: {nationality_name}
- Destino final: {destination_name} ({destination})
{transit_info}- Fecha de viaje: {travel_date.strftime('%Y-%m-%d') if travel_date else 'No especificada'}

PREGUNTA:
1. ¿Necesita visa para entrar a {destination_name}?
2. Si hay tránsitos, ¿necesita visa de tránsito?
3. ¿El pasaporte tiene validez suficiente? (mínimo requerido)
4. ¿Requiere vacunas obligatorias? (fiebre amarilla, COVID-19, etc.)

IMPORTANTE:
- Si el pasajero tiene nacionalidad {nationality_name}, considera las regulaciones específicas para ese país.
- Considera si {destination_name} forma parte de acuerdos como Espacio Schengen, MERCOSUR, etc.
- Para tránsitos, verifica si puede permanecer en zona internacional sin visa.

FORMATO DE RESPUESTA (JSON estricto):
{{
  "visa_required": true/false,
  "visa_type": "Tourist/Transit/Business/None",
  "passport_validity_ok": true/false,
  "passport_min_months": 6,
  "vaccination_required": ["Yellow Fever", "COVID-19"],
  "alert_level": "RED/YELLOW/GREEN",
  "summary": "Explicación breve y clara en español",
  "sources": ["URL1", "URL2"]
}}

NIVELES DE ALERTA:
- RED: Falta visa obligatoria o pasaporte vencido/insuficiente
- YELLOW: Requiere atención (visa de tránsito, vacunas, validez justa)
- GREEN: Todo en orden

Responde SOLO con el JSON, sin texto adicional."""

        return prompt
    
    def _parse_gemini_response(self, raw_text: str) -> MigrationValidationResult:
        """
        Parsea la respuesta de Gemini y extrae el JSON estructurado.
        
        Args:
            raw_text: Texto crudo de la respuesta de Gemini
        
        Returns:
            MigrationValidationResult parseado
        """
        try:
            # Intentar extraer JSON del texto
            # Gemini a veces envuelve el JSON en ```json ... ```
            json_text = raw_text.strip()
            
            if '```json' in json_text:
                json_text = json_text.split('```json')[1].split('```')[0].strip()
            elif '```' in json_text:
                json_text = json_text.split('```')[1].split('```')[0].strip()
            
            data = json.loads(json_text)
            
            return MigrationValidationResult(
                visa_required=data.get('visa_required', True),
                visa_type=data.get('visa_type', 'Unknown'),
                passport_validity_ok=data.get('passport_validity_ok', False),
                passport_min_months=data.get('passport_min_months', 6),
                vaccination_required=data.get('vaccination_required', []),
                alert_level=data.get('alert_level', 'YELLOW'),
                summary=data.get('summary', 'Verificar con embajada'),
                sources=data.get('sources', [])
            )
            
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            logger.warning(f"Error parseando respuesta de Gemini: {e}")
            logger.debug(f"Texto recibido: {raw_text}")
            
            # Fallback: intentar extraer información básica del texto
            return self._fallback_parse(raw_text)
    
    def _fallback_parse(self, raw_text: str) -> MigrationValidationResult:
        """Parser de respaldo si el JSON falla"""
        text_lower = raw_text.lower()
        
        # Heurísticas simples
        visa_required = 'visa' in text_lower and ('required' in text_lower or 'necesaria' in text_lower)
        passport_ok = 'válido' in text_lower or 'sufficient' in text_lower
        
        if 'red' in text_lower or 'crítica' in text_lower:
            alert_level = 'RED'
        elif 'green' in text_lower or 'orden' in text_lower:
            alert_level = 'GREEN'
        else:
            alert_level = 'YELLOW'
        
        return MigrationValidationResult(
            visa_required=visa_required,
            visa_type="Verificar con embajada",
            passport_validity_ok=passport_ok,
            passport_min_months=6,
            vaccination_required=[],
            alert_level=alert_level,
            summary=raw_text[:200] + "..." if len(raw_text) > 200 else raw_text,
            sources=[]
        )
