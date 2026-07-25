"""Servicio de hotel booking service para la aplicación bookings.
"""

from datetime import date

from django.db import transaction

from apps.bookings.models import (
    AlojamientoReserva,
    HotelTarifario,
    ItemVenta,
    ProductoServicio,
    TipoHabitacion,
    Venta,
)
from apps.common.models import Moneda


class HotelBookingService:
    """
    Servicio para orquestar la reserva de un hotel desde el tarifario.
    """

    @staticmethod
    def create_booking(
        hotel_id, tipo_hab_id, check_in, check_out, agencia, cliente=None, creado_por=None
    ):
        """
        Crea una reserva (Venta + Item + Alojamiento) basada en un hotel del tarifario.
        """
        hotel = HotelTarifario.objects.get(pk=hotel_id)
        tipo_hab = TipoHabitacion.objects.get(pk=tipo_hab_id)

        # Validar fechas
        if isinstance(check_in, str):
            check_in = date.fromisoformat(check_in)
        if isinstance(check_out, str):
            check_out = date.fromisoformat(check_out)

        noches = (check_out - check_in).days
        if noches <= 0:
            raise ValueError("La fecha de salida debe ser posterior al check-in.")

        # Buscar tarifa
        tarifa = tipo_hab.tarifas.filter(
            fecha_inicio__lte=check_in, fecha_fin__gte=check_out
        ).first()

        if not tarifa:
            raise ValueError("No hay tarifas disponibles para estas fechas.")

        # Calcular precio (Usamos DBL por defecto o la primera que tenga precio)
        precio_noche = tarifa.tarifa_dbl or tarifa.tarifa_sgl or tarifa.tarifa_tpl
        if not precio_noche:
            raise ValueError("No se encontró un precio válido en la tarifa.")

        subtotal = precio_noche * noches
        comision_monto = subtotal * (hotel.comision / 100)

        # Obtener moneda
        moneda_obj = Moneda.objects.filter(codigo_iso=tarifa.moneda).first()

        # Obtener ProductoServicio para 'Hotel'
        producto_hotel, _ = ProductoServicio.objects.get_or_create(
            nombre="Alojamiento / Hotel",
            defaults={
                "tipo_producto": "HTL",
                "activo": True,
                "codigo_interno": f"HOTEL_GENERICO_{agencia.pk}"
                if agencia
                else "HOTEL_GENERICO_GLOBAL",
            },
        )

        with transaction.atomic():
            # 1. Crear Venta
            venta = Venta.objects.create(
                agencia=agencia,
                cliente=cliente,
                creado_por=creado_por,
                moneda=moneda_obj,
                subtotal=subtotal,
                total_venta=subtotal,
                descripcion_general=f"Reserva de Hotel: {hotel.nombre} ({noches} noches)",
            )

            # 2. Crear ItemVenta
            item = ItemVenta.objects.create(
                agencia=agencia,
                venta=venta,
                producto_servicio=producto_hotel,
                descripcion_personalizada=f"{hotel.nombre} - {tipo_hab.nombre}",
                cantidad=1,
                precio_unitario_venta=subtotal,
                costo_neto_proveedor=subtotal - comision_monto,
                comision_agencia_monto=comision_monto,
                proveedor_servicio=hotel.tarifario.proveedor if hotel.tarifario else None,
                fecha_inicio_servicio=check_in,
                fecha_fin_servicio=check_out,
            )

            # 3. Crear AlojamientoReserva
            AlojamientoReserva.objects.create(
                agencia=agencia,
                venta=venta,
                item_venta=item,
                nombre_establecimiento=hotel.nombre,
                check_in=check_in,
                check_out=check_out,
                regimen_alimentacion=hotel.get_regimen_default_display(),
                habitaciones=1,
                proveedor=hotel.tarifario.proveedor if hotel.tarifario else None,
            )

            return venta
