from datetime import datetime
from decimal import Decimal

from django.db.models import Q
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.bookings.models import (
    HotelTarifario,
    TarifarioProveedor,
)
from core.auth_helpers import InternalAPIAuthMixin
from core.serializers_tarifario import (
    HotelTarifarioSerializer,
    TarifarioProveedorSerializer,
)


@extend_schema_view(
    list=extend_schema(
        description="Listar tarifarios de proveedores activos.", tags=["Tarifarios"]
    ),
    retrieve=extend_schema(
        description="Obtener detalle de un tarifario de proveedor.", tags=["Tarifarios"]
    ),
)
class TarifarioProveedorViewSet(InternalAPIAuthMixin, viewsets.ReadOnlyModelViewSet):
    """ViewSet para tarifarios de proveedores"""

    queryset = TarifarioProveedor.objects.filter(activo=True)
    serializer_class = TarifarioProveedorSerializer
    permission_classes = [IsAuthenticated]


@extend_schema_view(
    list=extend_schema(
        description="Listar hoteles en tarifarios activos con filtros.", tags=["Tarifarios"]
    ),
    retrieve=extend_schema(
        description="Obtener detalle de un hotel en tarifario.", tags=["Tarifarios"]
    ),
    cotizar=extend_schema(
        description="Cotizar hoteles según criterios de búsqueda (destino, fechas, ocupación).",
        request={
            "application/json": {
                "schema": {
                    "type": "object",
                    "properties": {
                        "destino": {"type": "string", "description": "Destino a buscar"},
                        "nombre_hotel": {
                            "type": "string",
                            "description": "Nombre específico del hotel",
                        },
                        "fecha_entrada": {
                            "type": "string",
                            "format": "date",
                            "description": "Fecha de check-in",
                        },
                        "fecha_salida": {
                            "type": "string",
                            "format": "date",
                            "description": "Fecha de check-out",
                        },
                        "habitaciones": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "tipo": {
                                        "type": "string",
                                        "enum": ["SGL", "DBL", "TPL"],
                                        "description": "Tipo de ocupación",
                                    },
                                    "adultos": {"type": "integer"},
                                    "ninos": {"type": "integer"},
                                },
                            },
                        },
                    },
                    "required": ["fecha_entrada", "fecha_salida"],
                }
            }
        },
        responses={
            200: {
                "description": "Cotización de hoteles con precios, desglose y neto después de comisión"
            }
        },
        tags=["Tarifarios"],
    ),
)
class HotelTarifarioViewSet(InternalAPIAuthMixin, viewsets.ReadOnlyModelViewSet):
    """ViewSet para hoteles en tarifarios"""

    queryset = HotelTarifario.objects.filter(activo=True).select_related(
        "tarifario", "tarifario__proveedor"
    )
    serializer_class = HotelTarifarioSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["destino", "regimen_default", "tarifario"]
    search_fields = ["nombre", "destino", "ubicacion_descripcion"]

    @action(detail=False, methods=["post"])
    def cotizar(self, request):
        """
        Cotiza hoteles según criterios de búsqueda

        POST /api/hoteles-tarifario/cotizar/
        {
            "destino": "Isla Margarita",
            "fecha_entrada": "2025-12-20",
            "fecha_salida": "2025-12-27",
            "habitaciones": [
                {"tipo": "DBL", "adultos": 2, "ninos": 0}
            ]
        }
        """
        destino = request.data.get("destino", "")
        nombre_hotel = request.data.get("nombre_hotel", "")
        fecha_entrada_str = request.data.get("fecha_entrada")
        fecha_salida_str = request.data.get("fecha_salida")
        habitaciones = request.data.get("habitaciones", [])

        if not fecha_entrada_str or not fecha_salida_str:
            return Response({"error": "Fechas requeridas"}, status=status.HTTP_400_BAD_REQUEST)

        fecha_entrada = datetime.strptime(fecha_entrada_str, "%Y-%m-%d").date()
        fecha_salida = datetime.strptime(fecha_salida_str, "%Y-%m-%d").date()
        noches = (fecha_salida - fecha_entrada).days

        if noches <= 0:
            return Response(
                {"error": "La fecha de salida debe ser posterior a la fecha de entrada"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Buscar hoteles disponibles
        query = Q(activo=True, tarifario__activo=True)
        if destino:
            query &= Q(destino__icontains=destino)
        if nombre_hotel:
            query &= Q(nombre__icontains=nombre_hotel)

        hoteles = (
            HotelTarifario.objects.filter(query)
            .select_related("tarifario")
            .prefetch_related("tipos_habitacion__tarifas")
        )

        # Cotizar cada hotel
        resultados = []
        for hotel in hoteles:
            cotizacion = self._cotizar_hotel(
                hotel, fecha_entrada, fecha_salida, habitaciones, noches
            )
            if cotizacion:
                resultados.append(cotizacion)

        # Ordenar por precio
        resultados.sort(key=lambda x: x["total_sin_comision"])

        return Response(
            {
                "destino": destino,
                "fecha_entrada": fecha_entrada,
                "fecha_salida": fecha_salida,
                "noches": noches,
                "hoteles_encontrados": len(resultados),
                "hoteles": resultados,
            }
        )

    def _cotizar_hotel(self, hotel, fecha_entrada, fecha_salida, habitaciones, noches):
        """Calcula precio total para un hotel"""
        total = Decimal("0.00")
        desglose = []

        for hab_req in habitaciones:
            tipo_ocupacion = hab_req.get("tipo", "DBL").lower()

            # Buscar tipo de habitación disponible
            for tipo_hab in hotel.tipos_habitacion.all():
                # Buscar tarifa vigente
                tarifa = tipo_hab.tarifas.filter(
                    fecha_inicio__lte=fecha_entrada, fecha_fin__gte=fecha_salida
                ).first()

                if tarifa:
                    # Obtener precio por noche según ocupación
                    precio_noche = getattr(tarifa, f"tarifa_{tipo_ocupacion}", None)

                    if precio_noche:
                        subtotal = precio_noche * noches
                        total += subtotal

                        desglose.append(
                            {
                                "tipo_habitacion": tipo_hab.nombre,
                                "ocupacion": tipo_ocupacion.upper(),
                                "precio_noche": float(precio_noche),
                                "noches": noches,
                                "subtotal": float(subtotal),
                                "temporada": tarifa.nombre_temporada or "Regular",
                                "moneda": tarifa.moneda,
                            }
                        )
                        break  # Usar primera habitación disponible

        if total > 0:
            comision_monto = total * (hotel.comision / 100)
            total_neto = total - comision_monto

            return {
                "hotel": hotel.nombre,
                "destino": hotel.destino,
                "regimen": hotel.get_regimen_display(),
                "comision": float(hotel.comision),
                "total_sin_comision": float(total),
                "comision_monto": float(comision_monto),
                "total_neto": float(total_neto),
                "desglose": desglose,
                "politica_ninos": getattr(hotel, "politica_ninos", "")
                or getattr(hotel, "politicas", ""),
                "check_in": str(hotel.check_in),
                "check_out": str(hotel.check_out),
            }

        return None
