"""
Servicio de integración contable para facturas.
Genera asientos contables automáticos según normativa VEN-NIF.
"""

import logging
from decimal import Decimal

from django.db import transaction

# Resolved dynamically to avoid circular dependencies

logger = logging.getLogger(__name__)


def generar_asiento_factura(factura):
    """
    Genera asiento contable automático para una factura.

    Asiento tipo:
    DEBE:
        - Cuentas por Cobrar Clientes (monto_total)
    HABER:
        - Ingresos por Ventas (subtotal_base_gravada + subtotal_exento + subtotal_exportacion)
        - IVA por Pagar (monto_iva_16 + monto_iva_adicional)
        - IGTF por Pagar (monto_igtf)

    Args:
        factura: Instancia de Factura

    Returns:
        AsientoContable: Asiento generado
    """
    from django.apps import apps

    AsientoContable = apps.get_model("contabilidad", "AsientoContable")
    MovimientoContable = apps.get_model("contabilidad", "MovimientoContable")
    CuentaContable = apps.get_model("contabilidad", "CuentaContable")
    try:
        with transaction.atomic():
            # Reutilizar o crear asiento contable
            asiento = AsientoContable.objects.filter(
                referencia_documento=factura.numero_control, agencia=factura.agencia
            ).first()

            if asiento:
                asiento.detalles_asiento.all().delete()
                asiento.fecha_contable = factura.fecha_emision
                asiento.tasa_cambio_aplicada = factura.tasa_bcv_aplicada or Decimal("1.00")
                asiento.descripcion_general = f"Factura {factura.numero_control} - {factura.cliente.nombres if factura.cliente else ''} {factura.cliente.apellidos if factura.cliente and factura.cliente.apellidos else ''}"
                asiento.save()
            else:
                asiento = AsientoContable.objects.create(
                    tipo_asiento=AsientoContable.TipoAsiento.VENTAS,
                    fecha_contable=factura.fecha_emision,
                    descripcion_general=f"Factura {factura.numero_control} - {factura.cliente.nombres if factura.cliente else ''} {factura.cliente.apellidos if factura.cliente and factura.cliente.apellidos else ''}",
                    tasa_cambio_aplicada=factura.tasa_bcv_aplicada or Decimal("1.00"),
                    referencia_documento=factura.numero_control,
                    estado=AsientoContable.EstadoAsiento.BORRADOR,
                    agencia=factura.agencia,
                )

            tasa = factura.tasa_bcv_aplicada or Decimal("1.00")
            linea_idx = 1

            # DEBE: Cuentas por Cobrar
            cuenta_cxc = CuentaContable.objects.filter(
                codigo_cuenta__startswith="1.1.2",  # Cuentas por Cobrar
                permite_movimientos=True,
                agencia=factura.agencia,
            ).first()

            if not cuenta_cxc:
                cuenta_cxc = CuentaContable.objects.filter(
                    codigo_cuenta__startswith="1",
                    permite_movimientos=True,
                    agencia=factura.agencia,
                ).first()

            if cuenta_cxc:
                monto_total = factura.gran_total_usd or Decimal("0.00")
                monto_total_bsd = (monto_total * tasa).quantize(Decimal("0.01"))
                MovimientoContable.objects.create(
                    asiento=asiento,
                    linea=linea_idx,
                    cuenta_contable=cuenta_cxc,
                    debe=monto_total,
                    haber=Decimal("0.00"),
                    debe_bsd=monto_total_bsd,
                    haber_bsd=Decimal("0.00"),
                    descripcion_linea=f"CxC Cliente {factura.cliente.nombres if factura.cliente else ''}",
                    agencia=factura.agencia,
                )
                linea_idx += 1

            # HABER: Ingresos por Ventas
            cuenta_ingresos = CuentaContable.objects.filter(
                codigo_cuenta__startswith="4.1",  # Ingresos
                permite_movimientos=True,
                agencia=factura.agencia,
            ).first()

            if not cuenta_ingresos:
                cuenta_ingresos = CuentaContable.objects.filter(
                    codigo_cuenta__startswith="4",
                    permite_movimientos=True,
                    agencia=factura.agencia,
                ).first()

            if cuenta_ingresos:
                monto_ingresos = factura.subtotal_usd or Decimal("0.00")
                if monto_ingresos > 0:
                    monto_ingresos_bsd = (monto_ingresos * tasa).quantize(Decimal("0.01"))
                    MovimientoContable.objects.create(
                        asiento=asiento,
                        linea=linea_idx,
                        cuenta_contable=cuenta_ingresos,
                        debe=Decimal("0.00"),
                        haber=monto_ingresos,
                        debe_bsd=Decimal("0.00"),
                        haber_bsd=monto_ingresos_bsd,
                        descripcion_linea=f"Ingresos Factura {factura.numero_control}",
                        agencia=factura.agencia,
                    )
                    linea_idx += 1

            # HABER: IVA por Pagar
            monto_iva_total = factura.total_iva_usd or Decimal("0.00")
            if monto_iva_total > 0:
                cuenta_iva = CuentaContable.objects.filter(
                    codigo_cuenta__startswith="2.1.4",  # IVA por Pagar
                    permite_movimientos=True,
                    agencia=factura.agencia,
                ).first()

                if not cuenta_iva:
                    cuenta_iva = CuentaContable.objects.filter(
                        codigo_cuenta__startswith="2",
                        permite_movimientos=True,
                        agencia=factura.agencia,
                    ).first()

                if cuenta_iva:
                    monto_iva_bsd = (monto_iva_total * tasa).quantize(Decimal("0.01"))
                    MovimientoContable.objects.create(
                        asiento=asiento,
                        linea=linea_idx,
                        cuenta_contable=cuenta_iva,
                        debe=Decimal("0.00"),
                        haber=monto_iva_total,
                        debe_bsd=Decimal("0.00"),
                        haber_bsd=monto_iva_bsd,
                        descripcion_linea=f"IVA Factura {factura.numero_control}",
                        agencia=factura.agencia,
                    )
                    linea_idx += 1

            # HABER: IGTF por Pagar
            monto_igtf = factura.total_igtf_usd or Decimal("0.00")
            if monto_igtf > 0:
                cuenta_igtf = CuentaContable.objects.filter(
                    codigo_cuenta__startswith="2.1.5",  # IGTF por Pagar
                    permite_movimientos=True,
                    agencia=factura.agencia,
                ).first()

                if not cuenta_igtf:
                    cuenta_igtf = CuentaContable.objects.filter(
                        codigo_cuenta__startswith="2",
                        permite_movimientos=True,
                        agencia=factura.agencia,
                    ).first()

                if cuenta_igtf:
                    monto_igtf_bsd = (monto_igtf * tasa).quantize(Decimal("0.01"))
                    MovimientoContable.objects.create(
                        asiento=asiento,
                        linea=linea_idx,
                        cuenta_contable=cuenta_igtf,
                        debe=Decimal("0.00"),
                        haber=monto_igtf,
                        debe_bsd=Decimal("0.00"),
                        haber_bsd=monto_igtf_bsd,
                        descripcion_linea=f"IGTF 3% Factura {factura.numero_control}",
                        agencia=factura.agencia,
                    )

            # Calcular totales y cuadrar el asiento
            asiento.calcular_totales()

            logger.info(
                f"Asiento contable generado: {asiento.id_asiento} para factura {factura.numero_control}"
            )
            return asiento

    except Exception as e:
        logger.error(f"Error generando asiento para factura {factura.numero_control}: {str(e)}")
        raise


def contabilizar_factura(factura):
    """
    Genera y contabiliza (aprueba) el asiento de la factura.

    Args:
        factura: Instancia de Factura

    Returns:
        bool: True si se contabilizó exitosamente
    """
    from django.apps import apps

    AsientoContable = apps.get_model("contabilidad", "AsientoContable")
    try:
        # Generar asiento siempre (no hay FK para lookup)
        asiento = generar_asiento_factura(factura)

        # Aprobar asiento
        if asiento and asiento.estado == AsientoContable.EstadoAsiento.BORRADOR:
            asiento.estado = AsientoContable.EstadoAsiento.CONTABILIZADO
            asiento.save()
            logger.info(
                f"Asiento {asiento.id_asiento} aprobado para factura {factura.numero_control}"
            )

        return True

    except Exception as e:
        logger.error(f"Error contabilizando factura {factura.numero_control}: {str(e)}")
        return False


def generar_asiento_pago(pago_venta):
    """
    Genera o actualiza el asiento contable para un cobro/pago de cliente.
    Si el pago ya tiene asiento y pasa a confirmado=False, se anula el asiento.
    Si el pago se confirma, se genera/actualiza el asiento:
    DEBE: Banco/Caja (según método de pago)
    HABER: Cuentas por Cobrar Clientes
    """
    from django.apps import apps

    AsientoContable = apps.get_model("contabilidad", "AsientoContable")
    MovimientoContable = apps.get_model("contabilidad", "MovimientoContable")
    CuentaContable = apps.get_model("contabilidad", "CuentaContable")

    referencia = f"PAGO-{pago_venta.pk}"
    asiento = AsientoContable.objects.filter(
        referencia_documento=referencia, agencia=pago_venta.agencia
    ).first()

    # Si pasa a no confirmado o se anula, cambiar estado del asiento a ANULADO
    if not pago_venta.confirmado:
        if asiento and asiento.estado != AsientoContable.EstadoAsiento.ANULADO:
            asiento.estado = AsientoContable.EstadoAsiento.ANULADO
            asiento.save(update_fields=["estado"])
            logger.info(f"Asiento contable {asiento.id_asiento} anulado para pago {pago_venta.pk}")
        return asiento

    # Si se confirma, crear o reactivar/actualizar asiento
    try:
        with transaction.atomic():
            if asiento:
                asiento.detalles_asiento.all().delete()
                asiento.fecha_contable = (
                    pago_venta.fecha_pago.date()
                    if hasattr(pago_venta.fecha_pago, "date")
                    else pago_venta.fecha_pago
                )
                asiento.estado = AsientoContable.EstadoAsiento.BORRADOR
                asiento.save()
            else:
                asiento = AsientoContable.objects.create(
                    tipo_asiento=AsientoContable.TipoAsiento.DIARIO,
                    fecha_contable=pago_venta.fecha_pago.date()
                    if hasattr(pago_venta.fecha_pago, "date")
                    else pago_venta.fecha_pago,
                    descripcion_general=f"Cobro/Pago Recibido - Ref: {pago_venta.referencia or 'S/R'}",
                    moneda=pago_venta.moneda,
                    tasa_cambio_aplicada=Decimal("1.00"),
                    referencia_documento=referencia,
                    estado=AsientoContable.EstadoAsiento.BORRADOR,
                    agencia=pago_venta.agencia,
                )

            # Buscar cuenta de Disponibilidades (Caja o Banco)
            if pago_venta.metodo == "EFE":
                # Caja
                cuenta_debe = CuentaContable.objects.filter(
                    codigo_cuenta__startswith="1.1.1",
                    permite_movimientos=True,
                    agencia=pago_venta.agencia,
                ).first()
            else:
                # Banco
                cuenta_debe = CuentaContable.objects.filter(
                    codigo_cuenta__startswith="1.1.2",
                    permite_movimientos=True,
                    agencia=pago_venta.agencia,
                ).first()

            if not cuenta_debe:
                cuenta_debe = CuentaContable.objects.filter(
                    codigo_cuenta__startswith="1",
                    permite_movimientos=True,
                    agencia=pago_venta.agencia,
                ).first()

            # Cuenta por Cobrar Clientes (Haber)
            cuenta_haber = CuentaContable.objects.filter(
                codigo_cuenta__startswith="1.1.2.01",
                permite_movimientos=True,
                agencia=pago_venta.agencia,
            ).first()

            if not cuenta_haber:
                cuenta_haber = CuentaContable.objects.filter(
                    codigo_cuenta__startswith="1",
                    permite_movimientos=True,
                    agencia=pago_venta.agencia,
                ).first()

            tasa = Decimal("1.00")
            monto_pago = pago_venta.monto + (pago_venta.monto_igtf or Decimal("0.00"))
            monto_bsd = (monto_pago * tasa).quantize(Decimal("0.01"))

            # Crear movimientos
            if cuenta_debe:
                MovimientoContable.objects.create(
                    asiento=asiento,
                    linea=1,
                    cuenta_contable=cuenta_debe,
                    debe=monto_pago,
                    haber=Decimal("0.00"),
                    debe_bsd=monto_bsd,
                    haber_bsd=Decimal("0.00"),
                    descripcion_linea=f"Cobro Método {pago_venta.get_metodo_display()}",
                    agencia=pago_venta.agencia,
                )

            if cuenta_haber:
                MovimientoContable.objects.create(
                    asiento=asiento,
                    linea=2,
                    cuenta_contable=cuenta_haber,
                    debe=Decimal("0.00"),
                    haber=monto_pago,
                    debe_bsd=Decimal("0.00"),
                    haber_bsd=monto_bsd,
                    descripcion_linea=f"Abono Cliente - Venta {pago_venta.venta.localizador if pago_venta.venta else ''}",
                    agencia=pago_venta.agencia,
                )

            asiento.calcular_totales()
            logger.info(
                f"Asiento contable {asiento.id_asiento} generado/actualizado para pago {pago_venta.pk}"
            )
            return asiento

    except Exception as e:
        logger.error(f"Error generando asiento para pago {pago_venta.pk}: {e}")
        raise
