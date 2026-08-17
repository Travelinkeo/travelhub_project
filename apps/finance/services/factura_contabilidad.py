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
    from django.contrib.contenttypes.models import ContentType

    AsientoContable = apps.get_model("contabilidad", "AsientoContable")
    MovimientoContable = apps.get_model("contabilidad", "MovimientoContable")
    CuentaContable = apps.get_model("contabilidad", "CuentaContable")
    try:
        with transaction.atomic():
            ct = ContentType.objects.get_for_model(factura)
            asiento = AsientoContable.objects.filter(
                content_type=ct, object_id=factura.pk, agencia=factura.agencia
            ).first()

            glosa = f"Factura {factura.numero_control} - {factura.cliente.nombres if factura.cliente else ''} {factura.cliente.apellidos if factura.cliente and factura.cliente.apellidos else ''}".strip()

            if asiento:
                asiento.movimientos.all().delete()
                asiento.fecha_contable = factura.fecha_emision
                asiento.glosa = glosa
                asiento.save()
            else:
                asiento = AsientoContable.objects.create(
                    tipo_asiento=AsientoContable.TipoAsiento.VENTAS,
                    fecha_contable=factura.fecha_emision,
                    glosa=glosa,
                    content_type=ct,
                    object_id=factura.pk,
                    estado=AsientoContable.EstadoAsiento.BORRADOR,
                    agencia=factura.agencia,
                )

            tasa = factura.tasa_bcv_aplicada or Decimal("1.00")

            # DEBE: Cuentas por Cobrar
            cuenta_cxc = CuentaContable.objects.filter(
                codigo_cuenta__startswith="1.1.2",
                acepta_movimientos=True,
                agencia=factura.agencia,
            ).first()

            if not cuenta_cxc:
                cuenta_cxc = CuentaContable.objects.filter(
                    codigo_cuenta__startswith="1",
                    acepta_movimientos=True,
                    agencia=factura.agencia,
                ).first()

            if cuenta_cxc:
                monto_total = factura.gran_total_usd or Decimal("0.00")
                monto_total_bsd = (monto_total * tasa).quantize(Decimal("0.01"))
                MovimientoContable.objects.create(
                    asiento=asiento,
                    cuenta=cuenta_cxc,
                    tipo=MovimientoContable.TipoMovimiento.DEBITO,
                    monto_usd=monto_total,
                    monto_ves=monto_total_bsd,
                    agencia=factura.agencia,
                )

            # HABER: Ingresos por Ventas
            cuenta_ingresos = CuentaContable.objects.filter(
                codigo_cuenta__startswith="4.1",
                acepta_movimientos=True,
                agencia=factura.agencia,
            ).first()

            if not cuenta_ingresos:
                cuenta_ingresos = CuentaContable.objects.filter(
                    codigo_cuenta__startswith="4",
                    acepta_movimientos=True,
                    agencia=factura.agencia,
                ).first()

            if cuenta_ingresos:
                monto_ingresos = factura.subtotal_usd or Decimal("0.00")
                if monto_ingresos > 0:
                    monto_ingresos_bsd = (monto_ingresos * tasa).quantize(Decimal("0.01"))
                    MovimientoContable.objects.create(
                        asiento=asiento,
                        cuenta=cuenta_ingresos,
                        tipo=MovimientoContable.TipoMovimiento.CREDITO,
                        monto_usd=monto_ingresos,
                        monto_ves=monto_ingresos_bsd,
                        agencia=factura.agencia,
                    )

            # HABER: IVA por Pagar
            monto_iva_total = factura.total_iva_usd or Decimal("0.00")
            if monto_iva_total > 0:
                cuenta_iva = CuentaContable.objects.filter(
                    codigo_cuenta__startswith="2.1.4",
                    acepta_movimientos=True,
                    agencia=factura.agencia,
                ).first()

                if not cuenta_iva:
                    cuenta_iva = CuentaContable.objects.filter(
                        codigo_cuenta__startswith="2",
                        acepta_movimientos=True,
                        agencia=factura.agencia,
                    ).first()

                if cuenta_iva:
                    monto_iva_bsd = (monto_iva_total * tasa).quantize(Decimal("0.01"))
                    MovimientoContable.objects.create(
                        asiento=asiento,
                        cuenta=cuenta_iva,
                        tipo=MovimientoContable.TipoMovimiento.CREDITO,
                        monto_usd=monto_iva_total,
                        monto_ves=monto_iva_bsd,
                        agencia=factura.agencia,
                    )

            # HABER: IGTF por Pagar
            monto_igtf = factura.total_igtf_usd or Decimal("0.00")
            if monto_igtf > 0:
                cuenta_igtf = CuentaContable.objects.filter(
                    codigo_cuenta__startswith="2.1.5",
                    acepta_movimientos=True,
                    agencia=factura.agencia,
                ).first()

                if not cuenta_igtf:
                    cuenta_igtf = CuentaContable.objects.filter(
                        codigo_cuenta__startswith="2",
                        acepta_movimientos=True,
                        agencia=factura.agencia,
                    ).first()

                if cuenta_igtf:
                    monto_igtf_bsd = (monto_igtf * tasa).quantize(Decimal("0.01"))
                    MovimientoContable.objects.create(
                        asiento=asiento,
                        cuenta=cuenta_igtf,
                        tipo=MovimientoContable.TipoMovimiento.CREDITO,
                        monto_usd=monto_igtf,
                        monto_ves=monto_igtf_bsd,
                        agencia=factura.agencia,
                    )

            logger.info(
                f"Asiento contable generado: {asiento.pk} para factura {factura.numero_control}"
            )
            return asiento

    except Exception as e:
        logger.error(f"Error generando asiento para factura {factura.numero_control}: {str(e)}")
        return None


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
        asiento = generar_asiento_factura(factura)

        # Aprobar asiento
        if asiento and asiento.estado == AsientoContable.EstadoAsiento.BORRADOR:
            asiento.estado = AsientoContable.EstadoAsiento.CONTABILIZADO
            asiento.save()
            logger.info(f"Asiento {asiento.pk} aprobado para factura {factura.numero_control}")

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
    from django.contrib.contenttypes.models import ContentType

    AsientoContable = apps.get_model("contabilidad", "AsientoContable")
    MovimientoContable = apps.get_model("contabilidad", "MovimientoContable")
    CuentaContable = apps.get_model("contabilidad", "CuentaContable")

    ct = ContentType.objects.get_for_model(pago_venta)
    asiento = AsientoContable.objects.filter(
        content_type=ct, object_id=pago_venta.pk, agencia=pago_venta.agencia
    ).first()

    # Si pasa a no confirmado o se anula, cambiar estado del asiento a ANULADO
    if not pago_venta.confirmado:
        if asiento and asiento.estado != AsientoContable.EstadoAsiento.ANULADO:
            asiento.estado = AsientoContable.EstadoAsiento.ANULADO
            asiento.save(update_fields=["estado"])
            logger.info(f"Asiento contable {asiento.pk} anulado para pago {pago_venta.pk}")
        return asiento

    # Si se confirma, crear o reactivar/actualizar asiento
    try:
        with transaction.atomic():
            fecha_c = (
                pago_venta.fecha_pago.date()
                if hasattr(pago_venta.fecha_pago, "date")
                else pago_venta.fecha_pago
            )
            glosa = f"Cobro/Pago Recibido - Ref: {pago_venta.referencia or 'S/R'}"

            if asiento:
                asiento.movimientos.all().delete()
                asiento.fecha_contable = fecha_c
                asiento.glosa = glosa
                asiento.estado = AsientoContable.EstadoAsiento.BORRADOR
                asiento.save()
            else:
                asiento = AsientoContable.objects.create(
                    tipo_asiento=AsientoContable.TipoAsiento.DIARIO,
                    fecha_contable=fecha_c,
                    glosa=glosa,
                    content_type=ct,
                    object_id=pago_venta.pk,
                    estado=AsientoContable.EstadoAsiento.BORRADOR,
                    agencia=pago_venta.agencia,
                )

            # Buscar cuenta de Disponibilidades (Caja o Banco)
            if pago_venta.metodo == "EFE":
                cuenta_debe = CuentaContable.objects.filter(
                    codigo_cuenta__startswith="1.1.1",
                    acepta_movimientos=True,
                    agencia=pago_venta.agencia,
                ).first()
            else:
                cuenta_debe = CuentaContable.objects.filter(
                    codigo_cuenta__startswith="1.1.2",
                    acepta_movimientos=True,
                    agencia=pago_venta.agencia,
                ).first()

            if not cuenta_debe:
                cuenta_debe = CuentaContable.objects.filter(
                    codigo_cuenta__startswith="1",
                    acepta_movimientos=True,
                    agencia=pago_venta.agencia,
                ).first()

            cuenta_haber = CuentaContable.objects.filter(
                codigo_cuenta__startswith="1.1.2.01",
                acepta_movimientos=True,
                agencia=pago_venta.agencia,
            ).first()

            if not cuenta_haber:
                cuenta_haber = CuentaContable.objects.filter(
                    codigo_cuenta__startswith="1",
                    acepta_movimientos=True,
                    agencia=pago_venta.agencia,
                ).first()

            monto_pago = pago_venta.monto + (pago_venta.monto_igtf or Decimal("0.00"))
            monto_ves = Decimal("0.00")

            if cuenta_debe:
                MovimientoContable.objects.create(
                    asiento=asiento,
                    cuenta=cuenta_debe,
                    tipo=MovimientoContable.TipoMovimiento.DEBITO,
                    monto_usd=monto_pago,
                    monto_ves=monto_ves,
                    agencia=pago_venta.agencia,
                )

            if cuenta_haber:
                MovimientoContable.objects.create(
                    asiento=asiento,
                    cuenta=cuenta_haber,
                    tipo=MovimientoContable.TipoMovimiento.CREDITO,
                    monto_usd=monto_pago,
                    monto_ves=monto_ves,
                    agencia=pago_venta.agencia,
                )

            logger.info(
                f"Asiento contable {asiento.pk} generado/actualizado para pago {pago_venta.pk}"
            )
            return asiento

    except Exception as e:
        logger.error(f"Error generando asiento para pago {pago_venta.pk}: {e}")
        return None
