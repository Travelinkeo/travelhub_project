# Archivo: core/views/translator_views.py

import logging
from decimal import InvalidOperation

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db import DatabaseError, IntegrityError
from django.views.generic import TemplateView
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.models import Aerolinea
from apps.finance.models import TasaCambioBCV
from core.auth_helpers import internal_auth

from ..itinerary_translator import ItineraryTranslator, TicketCalculator

logger = logging.getLogger(__name__)


class TraductorView(LoginRequiredMixin, TemplateView):
    """TraductorView."""

    template_name = "core/tools/traductor.html"

    def get_context_data(self, **kwargs):
        """get_context_data."""
        context = super().get_context_data(**kwargs)
        # Obtener tasa BCV para la calculadora
        try:
            tasa = TasaCambioBCV.objects.latest("fecha")
            context["tasa_bcv"] = tasa.tasa_bsd_por_usd
        except Exception:
            context["tasa_bcv"] = 0
        return context


@extend_schema(
    description="Traducir un itinerario de texto plano de cualquier GDS (SABRE, AMADEUS, KIU) a formato HTML legible.",
    request={
        "application/json": {
            "schema": {
                "type": "object",
                "properties": {
                    "itinerary": {"type": "string", "description": "Texto plano del itinerario"},
                    "gds_system": {
                        "type": "string",
                        "enum": ["SABRE", "AMADEUS", "KIU"],
                        "description": "Sistema GDS de origen",
                    },
                },
                "required": ["itinerary"],
            }
        }
    },
    responses={200: {"description": "Itinerario traducido con HTML y datos estructurados"}},
    tags=["Traductor"],
)
@api_view(["POST"])
@internal_auth
@permission_classes([IsAuthenticated])
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
        itinerary = request.data.get("itinerary", "")
        gds_system = request.data.get("gds_system", "SABRE")

        if not itinerary.strip():
            return Response(
                {"error": "El itinerario no puede estar vacío"}, status=status.HTTP_400_BAD_REQUEST
            )

        translator = ItineraryTranslator()

        # El translator ahora devuelve un diccionario con html y structured_data
        result = translator.translate_itinerary(itinerary, gds_system)

        # Mantener compatibilidad con el frontend actual enviando 'translated_itinerary' como el HTML
        return Response(
            {
                "success": True,
                "translated_itinerary": result["html"],
                "structured_data": result["structured_data"],
                "gds_system": gds_system,
                "original_itinerary": itinerary,
                "error": result.get("error"),
            }
        )

    except Exception as e:
        logger.error(f"Error en translate_itinerary_api: {e}")
        return Response(
            {"error": "Error interno del servidor"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@extend_schema(
    description="Calcular precio final de boleto aéreo aplicando fees y porcentajes sobre tarifa base.",
    request={
        "application/json": {
            "schema": {
                "type": "object",
                "properties": {
                    "tarifa": {"type": "number", "description": "Tarifa base del boleto"},
                    "fee_consolidador": {"type": "number", "description": "Fee del consolidador"},
                    "fee_interno": {"type": "number", "description": "Fee interno de la agencia"},
                    "porcentaje": {"type": "number", "description": "Porcentaje adicional"},
                },
                "required": ["tarifa"],
            }
        }
    },
    responses={200: {"description": "Cálculo detallado del precio final"}},
    tags=["Traductor"],
)
@api_view(["POST"])
@internal_auth
@permission_classes([IsAuthenticated])
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
        tarifa = float(request.data.get("tarifa", 0))
        fee_consolidador = float(request.data.get("fee_consolidador", 0))
        fee_interno = float(request.data.get("fee_interno", 0))
        porcentaje = float(request.data.get("porcentaje", 0))

        if any(val < 0 for val in [tarifa, fee_consolidador, fee_interno, porcentaje]):
            return Response(
                {"error": "Los valores no pueden ser negativos"}, status=status.HTTP_400_BAD_REQUEST
            )

        result = TicketCalculator.calculate_ticket_price(
            tarifa, fee_consolidador, fee_interno, porcentaje
        )

        if "error" in result:
            return Response({"error": result["error"]}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"success": True, "calculation": result})

    except (ValueError, TypeError):
        return Response(
            {"error": "Valores numéricos inválidos"}, status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Error en calculate_ticket_price_api: {e}")
        return Response(
            {"error": "Error interno del servidor"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@extend_schema(
    description="Obtener la lista de sistemas GDS soportados (SABRE, AMADEUS, KIU).",
    responses={
        200: {"description": "Lista de sistemas GDS soportados con nombres y descripciones"}
    },
    tags=["Traductor"],
)
@api_view(["GET"])
@internal_auth
@permission_classes([IsAuthenticated])
def get_supported_gds_api(request):
    """
    API para obtener los sistemas GDS soportados.

    GET /api/translator/gds/
    """
    try:
        supported_gds = [
            {"code": "SABRE", "name": "Sabre", "description": "Sistema de reservas Sabre"},
            {"code": "AMADEUS", "name": "Amadeus", "description": "Sistema de reservas Amadeus"},
            {"code": "KIU", "name": "KIU", "description": "Sistema de reservas KIU"},
        ]

        return Response({"success": True, "supported_gds": supported_gds})

    except Exception as e:
        logger.error(f"Error en get_supported_gds_api: {e}")
        return Response(
            {"error": "Error interno del servidor"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@extend_schema(
    description="Obtener el catálogo completo de aerolíneas activas con código IATA.",
    responses={200: {"description": "Catálogo de aerolíneas con código, nombre y país"}},
    tags=["Traductor"],
)
@api_view(["GET"])
@internal_auth
@permission_classes([IsAuthenticated])
def get_airlines_catalog_api(request):
    """
    API para obtener el catálogo de aerolíneas.

    GET /api/translator/airlines/
    """
    try:
        airlines_list = []
        for airline in (
            Aerolinea.objects.filter(activa=True, codigo_iata__isnull=False)
            .exclude(codigo_iata="")
            .select_related("pais")
        ):
            try:
                airlines_list.append(
                    {
                        "code": airline.codigo_iata,
                        "name": airline.nombre or "Sin nombre",
                        "country": airline.pais.nombre if airline.pais else "No especificado",
                    }
                )
            except Exception as exc:
                logger.warning("Error procesando aerolínea: %s", exc)
                continue

        return Response({"success": True, "airlines": airlines_list, "total": len(airlines_list)})

    except Exception as e:
        logger.error(f"Error en get_airlines_catalog_api: {e}")
        return Response(
            {"error": "Error interno del servidor"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@extend_schema(
    description="Obtener el catálogo de aeropuertos disponibles para el traductor de itinerarios.",
    responses={200: {"description": "Catálogo de aeropuertos con código y nombre"}},
    tags=["Traductor"],
)
@api_view(["GET"])
@internal_auth
@permission_classes([IsAuthenticated])
def get_airports_catalog_api(request):
    """
    API para obtener el catálogo de aeropuertos.

    GET /api/translator/airports/
    """
    try:
        translator = ItineraryTranslator()
        airports = translator.airports

        airports_list = [{"code": code, "name": name} for code, name in airports.items()]

        return Response({"success": True, "airports": airports_list, "total": len(airports_list)})

    except Exception as e:
        logger.error(f"Error en get_airports_catalog_api: {e}")
        return Response(
            {"error": "Error interno del servidor"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@extend_schema(
    description="Validar el formato de un itinerario GDS sin traducirlo. Detecta líneas válidas e inválidas.",
    request={
        "application/json": {
            "schema": {
                "type": "object",
                "properties": {
                    "itinerary": {
                        "type": "string",
                        "description": "Texto del itinerario a validar",
                    },
                    "gds_system": {
                        "type": "string",
                        "enum": ["SABRE", "AMADEUS", "KIU"],
                        "description": "Sistema GDS",
                    },
                },
                "required": ["itinerary"],
            }
        }
    },
    responses={200: {"description": "Resultado de validación con líneas válidas e inválidas"}},
    tags=["Traductor"],
)
@api_view(["POST"])
@internal_auth
@permission_classes([IsAuthenticated])
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
        itinerary = request.data.get("itinerary", "")
        gds_system = request.data.get("gds_system", "SABRE")

        if not itinerary.strip():
            return Response(
                {"error": "El itinerario no puede estar vacío"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Validar formato básico
        lines = [line.strip() for line in itinerary.split("\n") if line.strip()]

        validation_result = {
            "is_valid": True,
            "total_lines": len(lines),
            "valid_lines": 0,
            "invalid_lines": [],
            "warnings": [],
        }

        import re

        for i, line in enumerate(lines, 1):
            if gds_system.upper() == "SABRE":
                # Patrón básico para SABRE
                pattern = r"^\s*\d+\s*[A-Z0-9]{2}\s*\d+\s*[A-Z]*\s+\d{2}[A-Z]{3}\s+\w\s+\w{3}\w{3}"
            elif gds_system.upper() == "AMADEUS":
                # Patrón básico para AMADEUS
                pattern = r"^\s*\d+\s*[A-Z]{2}\s*\d+[A-Z]*\s+[A-Z]\s+[A-Z0-9]{5}\s+\w\s+\w{3}\w{3}"
            elif gds_system.upper() == "KIU":
                # Patrón básico para KIU
                pattern = (
                    r"^\s*\d+\s+[A-Z0-9]{2}\s*\d+\s*[A-Z]*\s+\d{2}[A-Z]{3}\s+\w{2}\s+\w{3}\w{3}"
                )
            else:
                return Response(
                    {"error": f"Sistema GDS no soportado: {gds_system}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if re.match(pattern, line):
                validation_result["valid_lines"] += 1
            else:
                validation_result["invalid_lines"].append(
                    {
                        "line_number": i,
                        "content": line,
                        "reason": f"No coincide con el formato esperado para {gds_system}",
                    }
                )

        # Determinar si es válido
        if validation_result["invalid_lines"]:
            validation_result["is_valid"] = False

        # Agregar advertencias
        if validation_result["total_lines"] == 0:
            validation_result["warnings"].append("El itinerario está vacío")
        elif validation_result["valid_lines"] == 0:
            validation_result["warnings"].append("Ninguna línea tiene formato válido")
        elif validation_result["invalid_lines"]:
            validation_result["warnings"].append(
                f"{len(validation_result['invalid_lines'])} líneas tienen formato incorrecto"
            )

        return Response(
            {"success": True, "gds_system": gds_system, "validation": validation_result}
        )

    except Exception as e:
        logger.error(f"Error en validate_itinerary_format_api: {e}")
        return Response(
            {"error": "Error interno del servidor"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@extend_schema(
    description="Traducir múltiples itinerarios en lote (máximo 10). Cada uno puede usar un GDS diferente.",
    request={
        "application/json": {
            "schema": {
                "type": "object",
                "properties": {
                    "itineraries": {
                        "type": "array",
                        "maxItems": 10,
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string", "description": "ID único del itinerario"},
                                "itinerary": {
                                    "type": "string",
                                    "description": "Texto del itinerario",
                                },
                                "gds_system": {
                                    "type": "string",
                                    "enum": ["SABRE", "AMADEUS", "KIU"],
                                },
                            },
                        },
                        "description": "Lista de itinerarios a traducir",
                    },
                },
                "required": ["itineraries"],
            }
        }
    },
    responses={200: {"description": "Resultados por lote con resumen de éxitos/fallos"}},
    tags=["Traductor"],
)
@api_view(["POST"])
@internal_auth
@permission_classes([IsAuthenticated])
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
        itineraries = request.data.get("itineraries", [])

        if not itineraries or not isinstance(itineraries, list):
            return Response(
                {"error": "Se requiere una lista de itinerarios"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(itineraries) > 10:  # Límite de seguridad
            return Response(
                {"error": "Máximo 10 itinerarios por lote"}, status=status.HTTP_400_BAD_REQUEST
            )

        translator = ItineraryTranslator()
        results = []

        for item in itineraries:
            item_id = item.get("id", f"item_{len(results) + 1}")
            itinerary = item.get("itinerary", "")
            gds_system = item.get("gds_system", "SABRE")

            try:
                if not itinerary.strip():
                    results.append(
                        {
                            "id": item_id,
                            "success": False,
                            "error": "Itinerario vacío",
                            "translated_itinerary": None,
                        }
                    )
                    continue

                result = translator.translate_itinerary(itinerary, gds_system)

                results.append(
                    {
                        "id": item_id,
                        "success": True,
                        "translated_itinerary": result["html"],
                        "structured_data": result["structured_data"],
                        "gds_system": gds_system,
                        "original_itinerary": itinerary,
                    }
                )

            except Exception as e:
                logger.error(f"Error procesando itinerario {item_id}: {e}")
                results.append(
                    {"id": item_id, "success": False, "error": str(e), "translated_itinerary": None}
                )

        successful = sum(1 for r in results if r["success"])
        failed = len(results) - successful

        return Response(
            {
                "success": True,
                "summary": {"total": len(results), "successful": successful, "failed": failed},
                "results": results,
            }
        )

    except Exception as e:
        logger.error(f"Error en batch_translate_api: {e}")
        return Response(
            {"error": "Error interno del servidor"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@extend_schema(
    description="Crea una cotización automática a partir de datos estructurados de vuelos extraídos de un GDS.",
    request={
        "application/json": {
            "schema": {
                "type": "object",
                "properties": {
                    "structured_data": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "type": {"type": "string", "enum": ["flight", "flight_raw_kiu"]},
                                "airline_code": {"type": "string"},
                                "flight_number": {"type": "string"},
                                "origin": {"type": "string"},
                                "destination": {"type": "string"},
                                "date": {"type": "string", "format": "date"},
                            },
                        },
                    },
                },
                "required": ["structured_data"],
            }
        }
    },
    responses={
        200: {"description": "Cotización creada con redirect a edición"},
        400: {"description": "Datos insuficientes"},
    },
    tags=["Traductor"],
)
@api_view(["POST"])
@internal_auth
@permission_classes([IsAuthenticated])
def create_quote_from_gds_api(request):
    """
    Crea una Cotización a partir de datos estructurados de GDS.

    POST /api/translator/create-quote/
    {
        "structured_data": [...]
    }
    """
    from django.utils import timezone

    from apps.cotizaciones.models import Cotizacion, ItemCotizacion
    from apps.crm.models import Cliente

    try:
        flights_data = request.data.get("structured_data", [])

        if not flights_data:
            return Response(
                {"error": "No hay datos estructurados para crear la cotización"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 1. Obtener o crear Cliente Genérico "POR ASIGNAR"
        # Esto permite crear la cotización rápido y luego editar el cliente
        cliente_generico = Cliente.objects.filter(nombres__icontains="POR ASIGNAR").first()
        if not cliente_generico:
            # Fallback: Usar el primer cliente o crear uno
            if Cliente.objects.exists():
                cliente_generico = Cliente.objects.first()
            else:
                cliente_generico = Cliente.objects.create(
                    nombres="CLIENTE POR ASIGNAR",
                    apellidos="",
                    email="temp@travelhub.com",
                    telefono_principal="0000000000",
                )

        from apps.common.models import Moneda

        moneda_usd = Moneda.objects.filter(codigo_iso="USD").first()
        if not moneda_usd:
            moneda_usd = Moneda.objects.first()  # Fallback

        # 2. Crear Cabecera Cotización
        cotizacion = Cotizacion.objects.create(
            cliente=cliente_generico,
            consultor=request.user,
            fecha_emision=timezone.now().date(),
            estado=Cotizacion.EstadoCotizacion.BORRADOR,
            notas_internas="Generada automáticamente desde el Traductor GDS",
            moneda=moneda_usd,
        )

        # 3. Crear Items
        item_count = 0
        for flight in flights_data:
            # Validar que sea un vuelo
            if flight.get("type") not in ["flight", "flight_raw_kiu"]:
                continue

            flight_desc = f"Vuelo {flight.get('airline_code', 'XX')} {flight.get('flight_number', '')}: {flight.get('origin', '???')} - {flight.get('destination', '???')} ({flight.get('date', '')})"

            # Buscar Producto 'Boleto Aéreo' genérico
            from apps.bookings.models import ProductoServicio

            producto_vuelo = ProductoServicio.objects.filter(
                tipo_producto=ProductoServicio.TipoProductoChoices.BOLETO_AEREO
            ).first()

            # Si no existe, usar el primer producto cualquiera como fallback
            if not producto_vuelo:
                producto_vuelo = ProductoServicio.objects.first()

            ItemCotizacion.objects.create(
                cotizacion=cotizacion,
                producto_servicio=producto_vuelo,
                descripcion_personalizada=flight_desc,
                cantidad=1,
                precio_unitario=0,  # Se debe cotizar manualmente luego
                impuestos_item=0,
            )
            item_count += 1

        # Recalcular total (aunque sea 0)
        cotizacion.calcular_total()

        return Response(
            {
                "success": True,
                "message": f"Cotización creada con {item_count} items",
                "redirect_url": f"/cotizaciones/{cotizacion.pk}/editar/",
                "quote_id": cotizacion.pk,
            }
        )

    except (IntegrityError, DatabaseError):
        logger.exception("Error de BD creando cotización desde GDS")
        return Response(
            {"error": "Error de base de datos al crear la cotización"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    except (ValidationError, KeyError, TypeError, ValueError) as e:
        logger.warning("Datos inválidos creando cotización desde GDS: %s", e)
        return Response(
            {"error": f"Datos inválidos: {e}"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    except (InvalidOperation, ArithmeticError):
        logger.exception("Error matemático calculando total de cotización GDS")
        return Response(
            {"error": "Error en cálculos financieros"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    except Exception:
        logger.exception("Error inesperado creando cotización desde GDS")
        return Response(
            {"error": "Error interno al crear la cotización. Revise el log de soporte."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
