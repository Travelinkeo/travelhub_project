import json
import os
import logging
from django.conf import settings
from core.models_catalogos import Ciudad, Pais, Moneda

logger = logging.getLogger(__name__)

class CatalogNormalizationService:
    """
    Servicio Determinístico para la Normalización de Catálogos Maestros (IATA, Países, Monedas).
    Evita la creación de 'Unknown City' y asegura integridad multi-tenant.
    """
    _airports_master = None

    @classmethod
    def _load_airports(cls):
        if cls._airports_master is None:
            path = os.path.join(settings.BASE_DIR, 'core', 'data', 'airports_master.json')
            try:
                if os.path.exists(path):
                    with open(path, 'r', encoding='utf-8') as f:
                        cls._airports_master = json.load(f)
                    logger.info(f"✅ Master IATA loaded: {len(cls._airports_master)} airports.")
                else:
                    logger.warning(f"⚠️ Master IATA file not found at {path}")
                    cls._airports_master = {}
            except Exception as e:
                logger.error(f"❌ Error loading airports master: {str(e)}")
                cls._airports_master = {}
        return cls._airports_master

    @classmethod
    def get_or_create_ciudad_by_iata(cls, iata_code: str) -> Ciudad:
        """
        Busca o crea una ciudad en la DB usando el catálogo maestro IATA.
        Prioriza la búsqueda por el nuevo campo codigo_iata en la DB.
        """
        if not iata_code or len(iata_code) != 3:
            return None

        iata_code = iata_code.upper()
        
        # 1. Búsqueda rápida por código IATA en DB
        ciudad_db = Ciudad.objects.filter(codigo_iata=iata_code).first()
        if ciudad_db:
            return ciudad_db

        master = cls._load_airports()
        
        # 2. Buscar en el maestro
        info = master.get(iata_code)
        
        if not info:
            # Búsqueda reversa si el JSON tiene otra estructura
            for entry in master.values():
                if entry.get('iata') == iata_code:
                    info = entry
                    break
        
        if not info:
            logger.warning(f"🕵️ IATA {iata_code} no encontrado en el maestro.")
            # Fallback histórico: buscar por nombre aproximado
            return Ciudad.objects.filter(nombre__icontains=iata_code).first()

        city_name = info.get('city') or info.get('name')
        country_iso = info.get('country')
        state = info.get('state')

        # 3. Obtener o crear País
        pais_obj = None
        if country_iso:
            pais_obj, _ = Pais.objects.get_or_create(
                codigo_iso_2=country_iso.upper(),
                defaults={
                    'nombre': country_iso.upper(), 
                    'codigo_iso_3': country_iso.upper() + 'X'
                }
            )

        # 4. Obtener o crear Ciudad y asegurar el código IATA
        # Usamos nombre, país y estado para identificar la entidad
        ciudad_obj, created = Ciudad.objects.get_or_create(
            nombre=city_name,
            pais=pais_obj,
            region_estado=state,
            defaults={
                'codigo_iata': iata_code
            }
        )
        
        # Si la ciudad ya existía (ej. creada manualmente) pero no tenía el código IATA, lo enriquecemos
        if not created and not ciudad_obj.codigo_iata:
            ciudad_obj.codigo_iata = iata_code
            ciudad_obj.save(update_fields=['codigo_iata'])

        if created:
            logger.info(f"✨ Ciudad creada desde Maestro: {city_name} ({iata_code})")

        return ciudad_obj

    @classmethod
    def normalize_currency(cls, currency_code: str) -> Moneda:
        """Asegura que la moneda existe en el sistema."""
        if not currency_code: return None
        code = str(currency_code).strip().upper()[:3]
        moneda, _ = Moneda.objects.get_or_create(
            codigo_iso=code,
            defaults={'nombre': code}
        )
        return moneda
