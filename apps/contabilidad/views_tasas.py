# contabilidad/views_tasas.py
"""
API endpoints para tasas de cambio de Venezuela
"""

import logging
from datetime import date, datetime, timedelta

from django.core.cache import cache
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.finance.models import TasaCambioBCV
from core.auth_helpers import internal_auth

from .tasas_venezuela_client import TasasVenezuelaClient

logger = logging.getLogger(__name__)


@extend_schema(
    description="Obtiene las tasas de cambio vigentes de Venezuela (BCV oficial, promedio, P2P). Auto-actualiza cada 4 horas.",
    responses={
        200: {"description": "Tasas actuales de Venezuela"},
        503: {"description": "No se pudieron obtener las tasas"},
    },
    tags=["Tasas BCV"],
)
@api_view(["GET"])
@permission_classes([AllowAny])  # Público para mostrar en header
def obtener_tasas_actuales(request):
    """
    Obtiene las tasas actuales de cambio (BCV, Promedio, P2P).
    Auto-actualiza si han pasado más de 30 minutos desde última actualización.
    """
    cache_key = "tasas_venezuela_actuales"
    cache_timestamp_key = "tasas_venezuela_timestamp"

    # Verificar si necesita actualización (4 horas = 6 veces al día)
    last_update = cache.get(cache_timestamp_key)
    needs_update = not last_update or (datetime.now() - last_update) > timedelta(hours=4)

    if needs_update:
        # Actualizar tasas en background
        tasas = TasasVenezuelaClient.obtener_resumen_tasas()
        if tasas:
            cache.set(cache_key, tasas, 86400)  # 24 horas
            cache.set(cache_timestamp_key, datetime.now(), 86400)

    # Obtener del caché
    tasas_cached = cache.get(cache_key)

    if tasas_cached:
        return Response(tasas_cached)

    # Fallback a DB
    try:
        tasa_bcv_db = TasaCambioBCV.objects.filter(fecha=date.today()).first()
        if tasa_bcv_db:
            tasas = {
                "bcv": {
                    "valor": float(tasa_bcv_db.tasa_bsd_por_usd),
                    "fecha": tasa_bcv_db.fecha.strftime("%Y-%m-%d"),
                    "nombre": "BCV Oficial (DB)",
                }
            }
            cache.set(cache_key, tasas, 86400)
            return Response(tasas)
    except Exception as e:
        logger.warning(f"Excepción silenciosa capturada: {e}")
    return Response(
        {"error": "No se pudieron obtener las tasas"}, status=status.HTTP_503_SERVICE_UNAVAILABLE
    )


@extend_schema(
    description="Obtiene solo la tasa BCV oficial simplificada (ideal para headers y widgets).",
    responses={
        200: {"description": "Tasa BCV oficial"},
        404: {"description": "No hay tasas disponibles"},
    },
    tags=["Tasas BCV"],
)
@api_view(["GET"])
@permission_classes([AllowAny])
def obtener_tasa_bcv_simple(request):
    """
    Obtiene solo la tasa BCV oficial (simplificado para header).
    """
    cache_key = "tasa_bcv_simple"
    tasa_cached = cache.get(cache_key)

    if tasa_cached:
        return Response(tasa_cached)

    # Intentar API primero
    tasa_api = TasasVenezuelaClient.obtener_tasa_bcv()

    if tasa_api:
        resultado = {"valor": float(tasa_api), "fecha": date.today().strftime("%Y-%m-%d")}
    else:
        # Fallback a DB
        try:
            tasa_db = TasaCambioBCV.objects.filter(fecha=date.today()).first()
            if not tasa_db:
                tasa_db = TasaCambioBCV.objects.latest("fecha")

            resultado = {
                "valor": float(tasa_db.tasa_bsd_por_usd),
                "fecha": tasa_db.fecha.strftime("%Y-%m-%d"),
            }
        except TasaCambioBCV.DoesNotExist:
            return Response({"error": "No hay tasas disponibles"}, status=status.HTTP_404_NOT_FOUND)

    # Caché por 5 minutos
    cache.set(cache_key, resultado, 300)

    return Response(resultado)


@extend_schema(
    description="Sincroniza las tasas de cambio manualmente desde las fuentes oficiales.",
    responses={
        200: {"description": "Tasas sincronizadas correctamente"},
        500: {"description": "Error en la sincronización"},
    },
    tags=["Tasas BCV"],
)
@api_view(["POST"])
@internal_auth
def sincronizar_tasas_manual(request):
    """
    Sincroniza las tasas manualmente (requiere autenticación).
    """
    try:
        resultados = TasasVenezuelaClient.actualizar_tasas_db()

        # Limpiar caché
        try:
            cache.delete("tasas_venezuela_actuales")
            cache.delete("tasa_bcv_simple")
            cache.delete("tasa_bcv_context")
        except Exception as cache_err:
            logger.warning(f"No se pudo limpiar caché en sincronizar_tasas_manual: {cache_err}")

        return Response(
            {
                "success": True,
                "resultados": resultados,
                "mensaje": "Tasas sincronizadas correctamente",
            }
        )
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
