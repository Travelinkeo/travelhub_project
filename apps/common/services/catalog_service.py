from __future__ import annotations

import json
import logging
import os
from typing import Any

from django.conf import settings

from apps.common.models import Ciudad, Pais


def __getattr__(name: str) -> Any:
    if name == "Moneda":
        from django.apps import apps

        return apps.get_model("common", "Moneda")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


logger = logging.getLogger(__name__)


class CatalogNormalizationService:
    """
    Servicio Determinístico para la Normalización de Catálogos Maestros (IATA, Países, Monedas).
    Evita la creación de 'Unknown City' y asegura integridad multi-tenant.
    """

    _airports_master: dict[str, Any] | None = None
    # Índices secundarios construidos UNA sola vez (junto con _airports_master).
    # El airports_master.json está estructurado con llaves ICAO (no IATA), por
    # lo que necesitamos índices O(1) por IATA y por (CIUDAD, PAÍS) normalizada.
    _airports_by_iata: dict[str, dict[str, Any]] | None = None
    _airports_by_city: dict[str, list[dict[str, Any]]] | None = None

    # Alias manual para ciudades Venezolanas/LatAm que el GDS KIU imprime por
    # NOMBRE en la columna FROM/TO (no por IATA). Agregamos LAS QUE FALTAN para
    # que la normalización no se quede a ciegas.
    # Mapeo: UPPER(nombre_normalizado) -> IATA oficial
    CITY_NAME_ALIASES: dict[str, str] = {
        # Venezuela
        "SAN ANTONIO": "SVZ",  # San Antonio del Táchira (SVZ)
        "VALENCIA": "VLN",  # Valencia, Carabobo (VLN)
        "SANTO DOMINGO": "STD",  # Sto. Domingo, Táchira (STD) — Doméstico VE tiene prioridad
        "CARACAS": "CCS",
        "MARACAIBO": "MAR",
        "PTO ORDAZ": "PZO",  # Puerto Ordaz
        "PUERTO ORDAZ": "PZO",
        "BARQUISIMETO": "BRM",
        "MARIGUITAR": "MAY",  # Margarita
        "PORLAMAR": "PMV",
        "MERIDA": "MRD",
        "BARINAS": "BNS",
        "GUASDUALITO": "GDO",
        "LA FRIA": "LFR",
        "ACARIGUA": "AGV",
        "GUANARE": "GUQ",
        "CORO": "CZE",
        "PUNTO FIJO": "LSP",
        "EL VIGIA": "EJA",
        "TUMEREMO": "TMO",
        "SANTA ELENA DE UAIREN": "SFD",
        # Common Latin American domestic
        "BOGOTA": "BOG",
        "MEDELLIN": "MDE",
        "CALI": "CLO",
        "CARTAGENA": "CTG",
        "BUENOS AIRES": "EZE",
        "LIMA": "LIM",
        "QUITO": "UIO",
        "GUAYAQUIL": "GYE",
        "SANTO DOMINGO DO": "SDQ",  # República Dominicana (si país está explícito)
        "PANAMA": "PTY",
    }

    @classmethod
    def _load_airports(cls) -> dict[str, Any]:
        if not cls._airports_master:
            # BASE_DIR es definido en project settings (no por django-stubs).
            path = os.path.join(settings.BASE_DIR, "core", "data", "airports_master.json")  # type: ignore[misc]
            try:
                if os.path.exists(path):
                    with open(path, encoding="utf-8") as f:
                        loaded = json.load(f)
                    cls._airports_master = loaded if isinstance(loaded, dict) else {}
                    logger.info(f" Master IATA loaded: {len(cls._airports_master)} airports.")
                else:
                    logger.warning(f" Master IATA file not found at {path}")
                    cls._airports_master = {}
            except Exception as e:
                logger.error(f" Error loading airports master: {str(e)}")
                cls._airports_master = {}

            # Construir índices secundarios ahora para evitar iterar 29k entradas
            # por cada tramo de cada boleto.
            cls._airports_by_iata = {}
            cls._airports_by_city = {}
            for _icao_key, info in (cls._airports_master or {}).items():
                if not isinstance(info, dict):
                    continue
                iata = (info.get("iata") or "").strip().upper()
                if iata and len(iata) == 3 and iata not in cls._airports_by_iata:
                    cls._airports_by_iata[iata] = info
                city = (info.get("city") or "").strip().upper()
                if city:
                    cls._airports_by_city.setdefault(city, []).append(info)
        return cls._airports_master

    @classmethod
    def _get_airports_by_iata(cls, iata_code: str) -> dict[str, Any] | None:
        """Lookup O(1) por código IATA explícito (en el campo 'iata' del JSON)."""
        cls._load_airports()
        return (
            cls._airports_by_iata.get((iata_code or "").upper()) if cls._airports_by_iata else None
        )

    @classmethod
    def _get_airports_by_city(cls, city_name: str) -> list[dict[str, Any]]:
        """Lookup O(1) por nombre UPPER de ciudad. Devuelve lista de dicts de aeropuertos."""
        cls._load_airports()
        if not cls._airports_by_city:
            return []
        key = (city_name or "").strip().upper()
        return cls._airports_by_city.get(key, [])

    @classmethod
    def get_or_create_ciudad_by_iata(cls, iata_code: str) -> Ciudad | None:
        """
        Busca o crea una ciudad en la DB usando el catálogo maestro IATA.
        Prioriza la búsqueda por el nuevo campo codigo_iata en la DB.
        """
        if not iata_code or len(iata_code) != 3:
            return None

        iata_code = iata_code.upper()

        # 1. Búsqueda rápida por código IATA en DB
        try:
            ciudad_db = Ciudad.objects.filter(codigo_iata=iata_code).first()
        except Exception as e_db:
            # 🛡️ DB caída / RLS bloqueando / error de conexión: no tragar el parseo.
            logger.warning(
                f"⚠️ get_or_create_ciudad_by_iata: DB inaccesible para IATA {iata_code}: {e_db}. "
                "Devolviendo None (no bloquea el parseo)."
            )
            return None
        if ciudad_db:
            return ciudad_db

        # 2. Lookup O(1) por IATA en el índice secundario (no iterar master completo)
        info: dict[str, Any] | None = cls._get_airports_by_iata(iata_code)

        # 3. Fallback histórico: lookup lineal SOLO si el índice falló (raro)
        if not info:
            master = cls._load_airports()
            for entry in master.values():
                if isinstance(entry, dict) and entry.get("iata") == iata_code:
                    info = entry
                    break

        if not info:
            logger.warning(f" IATA {iata_code} no encontrado en el maestro.")
            # Fallback histórico: buscar por nombre aproximado
            try:
                return Ciudad.objects.filter(nombre__icontains=iata_code).first()
            except Exception as e_db:
                logger.warning(
                    f"⚠️ Fallback nombre también falló (DB) para IATA {iata_code}: {e_db}"
                )
                return None

        city_name: str | None = info.get("city") or info.get("name")
        country_iso: str | None = info.get("country")
        state: str | None = info.get("state")

        try:
            # 3. Obtener o crear País
            pais_obj: Pais | None = None
            if country_iso:
                pais_obj, _ = Pais.objects.get_or_create(
                    codigo_iso_2=country_iso.upper(),
                    defaults={
                        "nombre": country_iso.upper(),
                        "codigo_iso_3": country_iso.upper() + "X",
                    },
                )

            # 4. Obtener o crear Ciudad y asegurar el código IATA
            # Usamos nombre, país y estado para identificar la entidad
            ciudad_obj, created = Ciudad.objects.get_or_create(
                nombre=city_name,
                pais=pais_obj,
                region_estado=state,
                defaults={"codigo_iata": iata_code},
            )

            # Si la ciudad ya existía (ej. creada manualmente) pero no tenía el código IATA, lo enriquecemos
            if not created and not ciudad_obj.codigo_iata:
                ciudad_obj.codigo_iata = iata_code
                ciudad_obj.save(update_fields=["codigo_iata"])

            if created:
                logger.info(f" Ciudad creada desde Maestro: {city_name} ({iata_code})")

            return ciudad_obj
        except Exception as e_db:
            logger.warning(
                f"⚠️ get_or_create_ciudad_by_iata: no se pudo crear Ciudad {iata_code}: {e_db}. "
                "Devolviendo None (no bloquea el parseo)."
            )
            return None

    @classmethod
    def normalize_currency(cls, currency_code: str) -> Any:
        """Asegura que la moneda existe en el sistema."""
        if not currency_code:
            return None
        code = str(currency_code).strip().upper()[:3]
        from django.apps import apps

        Moneda = apps.get_model("common", "Moneda")
        moneda, _ = Moneda.objects.get_or_create(codigo_iso=code, defaults={"nombre": code})
        return moneda
