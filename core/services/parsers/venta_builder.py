import logging
from decimal import Decimal
from django.db import IntegrityError
from django.db.models import Sum
from django.utils import timezone

from core.models import Moneda
from apps.bookings.models import Venta, ItemVenta, BoletoImportado
from apps.crm.models import Cliente
from core.models_catalogos import ProductoServicio

logger = logging.getLogger(__name__)

class VentaBuilderService:
    """
    Microservicio encargado de crear los registros financieros y comerciales (Venta e ItemVenta).
    Responsabilidad Única: Integridad financiera en la base de datos.
    """

    @staticmethod
    def construir_venta_multipax(agencia, boletos_data: list, cliente_pagador: Cliente) -> Venta:
        """
        Orquestador para crear una Venta con múltiples boletos (pasajeros).
        boletos_data: Lista de diccionarios con la data de cada boleto (BoletoAereoSchema).
        """
        if not boletos_data:
            raise ValueError("No se recibieron datos de boletos para construir la venta.")

        # 1. Identificar PNR y Moneda (usamos el primero como referencia)
        primer_boleto = boletos_data[0]
        pnr = primer_boleto.get('codigo_reserva') or primer_boleto.get('CODIGO_RESERVA') or "SIN-PNR"
        moneda_codigo = str(primer_boleto.get('moneda') or primer_boleto.get('TOTAL_MONEDA') or "USD")[:3].upper()

        moneda, _ = Moneda.objects.get_or_create(
            codigo_iso=moneda_codigo,
            defaults={'nombre': moneda_codigo}
        )

        # 2. Crear o Recuperar la Venta base
        venta, created = Venta.objects.get_or_create(
            localizador=pnr,
            agencia=agencia,
            defaults={
                'cliente': cliente_pagador,
                'total_venta': Decimal("0.00"),
                'moneda': moneda,
                'estado': 'PEN',
                'canal_origen': 'IMP',
                'fecha_venta': timezone.now()
            }
        )

        if not created:
            logger.info(f"♻️ Reutilizando Venta {venta.pk} existente para PNR {pnr}")
            if cliente_pagador and (not venta.cliente or venta.cliente.id_cliente != cliente_pagador.id_cliente):
                venta.cliente = cliente_pagador
                venta.save(update_fields=['cliente'])

        # 3. Procesar cada boleto
        for b_data in boletos_data:
            # Creamos el registro de BoletoImportado
            pnr_b = str(b_data.get('codigo_reserva', pnr))[:10]
            num_tkt = str(b_data.get('numero_boleto', ''))[:50]
            nombre_pax = str(b_data.get('nombre_pasajero', ''))[:150]
            
            total_b = Decimal(str(b_data.get('total', 0)))
            tarifa_b = Decimal(str(b_data.get('tarifa', 0)))
            impuestos_b = Decimal(str(b_data.get('impuestos', 0)))

            boleto_obj = BoletoImportado.objects.create(
                agencia=agencia,
                estado_parseo='COM',
                localizador_pnr=pnr_b,
                numero_boleto=num_tkt,
                nombre_pasajero_completo=nombre_pax,
                datos_parseados=b_data,
                log_parseo="Inyectado vía GDS Analyzer (Multi-pax)",
                tarifa_base=tarifa_b,
                otros_impuestos_monto=impuestos_b,
                total_boleto=total_b,
                venta_asociada=venta
            )

            # Inyectar el ItemVenta correspondiente
            VentaBuilderService._crear_item_venta(venta, boleto_obj, b_data)

        # 4. Recalcular total de la venta
        VentaBuilderService._recalcular_total_venta(venta)

        logger.info(f"💳 Venta Multipax {pnr} ({len(boletos_data)} pax) construida exitosamente.")
        return venta

    @staticmethod
    def _crear_item_venta(venta: Venta, boleto: BoletoImportado, datos: dict):
        """Método interno para crear el item de venta."""
        producto = ProductoServicio.objects.filter(tipo_producto='AIR').order_by('-agencia').first()
        if not producto:
             producto = ProductoServicio.objects.first()

        total_monto = Decimal(str(datos.get('total') or datos.get('TOTAL') or 0))
        comision_pct = getattr(boleto.agencia, 'comision_default', Decimal("10.00"))
        
        if total_monto > 0:
            monto_comision = total_monto * (comision_pct / Decimal("100.00"))
            costo_neto = total_monto - monto_comision
        else:
            monto_comision = Decimal("0.00")
            costo_neto = Decimal("0.00")

        num_boleto = datos.get('numero_boleto') or datos.get('NUMERO_DE_BOLETO') or boleto.numero_boleto or "N/A"
        nombre_pax = datos.get('nombre_pasajero') or datos.get('NOMBRE_DEL_PASAJERO') or boleto.nombre_pasajero_completo or "Sin Nombre"
        pnr = datos.get('codigo_reserva') or datos.get('CODIGO_RESERVA') or venta.localizador
        
        descripcion = f"Boleto {num_boleto} - Pax: {nombre_pax} - PNR: {pnr}"
        
        ItemVenta.objects.update_or_create(
            venta=venta,
            descripcion_personalizada=descripcion, 
            defaults={
                'producto_servicio': producto,
                'codigo_reserva_proveedor': pnr,
                'cantidad': 1,
                'total_item_venta': total_monto,
                'precio_unitario_venta': total_monto,
                'costo_neto_proveedor': costo_neto,
                'comision_agencia_monto': monto_comision,
                'impuestos_item_venta': Decimal(str(datos.get('impuestos') or datos.get('IMPUESTOS') or 0))
            }
        )

    @staticmethod
    def _recalcular_total_venta(venta: Venta):
        """Recalcula el total de la venta basado en sus items."""
        total_real = ItemVenta.objects.filter(venta=venta).aggregate(Sum('total_item_venta'))['total_item_venta__sum'] or Decimal("0.00")
        venta.total_venta = total_real
        venta.save(update_fields=['total_venta'])

    @staticmethod
    def construir_venta(boleto: BoletoImportado, datos: dict, cliente_obj: Cliente) -> Venta:
        """Legado (Single-Pax): Envuelve la lógica nueva."""
        moneda_codigo = str(datos.get('TOTAL_MONEDA') or datos.get('moneda') or "USD")[:3].upper()
        moneda, _ = Moneda.objects.get_or_create(codigo_iso=moneda_codigo, defaults={'nombre': moneda_codigo})

        pnr = datos.get('CODIGO_RESERVA') or datos.get('pnr') or boleto.localizador_pnr or "SIN-PNR"
        
        venta, created = Venta.objects.get_or_create(
            localizador=pnr,
            agencia=boleto.agencia,
            defaults={
                'cliente': cliente_obj,
                'total_venta': Decimal("0.00"),
                'moneda': moneda,
                'estado': 'PEN',
                'canal_origen': 'IMP',
                'fecha_venta': timezone.now()
            }
        )
        
        if not created and cliente_obj:
            venta.cliente = cliente_obj
            venta.save(update_fields=['cliente'])

        boleto.venta_asociada = venta
        boleto.save(update_fields=['venta_asociada'])

        VentaBuilderService._crear_item_venta(venta, boleto, datos)
        VentaBuilderService._recalcular_total_venta(venta)
        
        return venta
