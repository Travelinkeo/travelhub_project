import logging

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from core.signals_bypass import are_signals_blocked, disable_signals

logger = logging.getLogger(__name__)


def _get_cuenta_banco_caja(metodo_pago, moneda):
    from apps.contabilidad.models import PlanContable

    query = PlanContable.objects.filter(tipo_cuenta="AC", permite_movimientos=True)

    termino = ""
    if metodo_pago == "EFE":
        termino = "Caja"
    elif metodo_pago in ["TRA", "TDC"]:
        termino = "Banco"
    elif metodo_pago == "ZEL":
        termino = "Zelle"

    cuentas = query.filter(nombre_cuenta__icontains=termino)

    moneda_str = moneda.codigo_iso
    cuentas_moneda = cuentas.filter(nombre_cuenta__icontains=moneda_str)

    if cuentas_moneda.exists():
        return cuentas_moneda.first()

    if cuentas.exists():
        return cuentas.first()

    return None


@receiver(post_save, sender="finance.GastoOperativo")
def contabilizar_gasto_operativo(sender, instance, created, **kwargs):
    from apps.contabilidad.models import AsientoContable, DetalleAsiento

    if are_signals_blocked():
        return

    try:
        cuenta_haber = _get_cuenta_banco_caja(instance.metodo_pago, instance.moneda)
        if not cuenta_haber:
            error_msg = f"Error Contable: No se configuro cuenta para {instance.metodo_pago} en {instance.moneda}"
            logger.error(error_msg)
            instance.estado_contable = "ERR"
            instance.error_contable_msg = error_msg
            with disable_signals():
                instance.save(update_fields=["estado_contable", "error_contable_msg"])
            return

        asiento = instance.asiento_contable
        if not asiento:
            asiento = AsientoContable.objects.create(
                fecha_contable=instance.fecha,
                descripcion_general=f"Gasto: {instance.descripcion}",
                tipo_asiento="DIA",
                moneda=instance.moneda,
                referencia_documento=f"GASTO-{instance.pk}",
                estado="BOR",
            )
            instance.asiento_contable = asiento
            with disable_signals():
                instance.save(update_fields=["asiento_contable"])
        else:
            asiento.fecha_contable = instance.fecha
            asiento.descripcion_general = f"Gasto: {instance.descripcion}"
            asiento.moneda = instance.moneda
            asiento.save()
            asiento.detalles_asiento.all().delete()

        DetalleAsiento.objects.create(
            asiento=asiento,
            linea=1,
            cuenta_contable=instance.categoria,
            debe=instance.monto,
            haber=0,
            descripcion_linea=f"Cargo a {instance.categoria.nombre_cuenta}",
        )

        DetalleAsiento.objects.create(
            asiento=asiento,
            linea=2,
            cuenta_contable=cuenta_haber,
            debe=0,
            haber=instance.monto,
            descripcion_linea=f"Pago con {instance.get_metodo_pago_display()}",
        )

        asiento.calcular_totales()

        instance.estado_contable = "PRO"
        instance.error_contable_msg = None
        with disable_signals():
            instance.save(update_fields=["estado_contable", "error_contable_msg"])

    except Exception as e:
        logger.error(f"Error contabilizando Gasto #{instance.pk}: {e}")


@receiver(post_delete, sender="finance.GastoOperativo")
def eliminar_asiento_gasto(sender, instance, **kwargs):
    if instance.asiento_contable:
        instance.asiento_contable.delete()
