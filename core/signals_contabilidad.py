import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _

from .models.contabilidad import AsientoContable, DetalleAsiento, PlanContable

logger = logging.getLogger(__name__)

def _get_cuenta_banco_caja(metodo_pago, moneda):
    """
    Intenta buscar la cuenta contable de activo (Caja/Banco) adecuada
    según el método de pago y la moneda.
    """
    # MAPEO DE CUENTAS (Esto debería estar en configuración, pero hardcodeamos heurística para MVP)
    # Buscamos cuentas que empiecen por '1' (Activo) y coincidan con el nombre
    
    query = PlanContable.objects.filter(tipo_cuenta='AC', permite_movimientos=True) # Activo
    
    termino = ""
    if metodo_pago == 'EFE':
        termino = "Caja"
    elif metodo_pago in ['TRA', 'TDC']:
        termino = "Banco"
    elif metodo_pago == 'ZEL':
        termino = "Zelle" # O "Caja Digital"
        
    # Filtrar por término
    cuentas = query.filter(nombre_cuenta__icontains=termino)
    
    # Filtrar heurística por moneda (si el nombre incluye USD o VES/BS)
    moneda_str = moneda.codigo_iso
    cuentas_moneda = cuentas.filter(nombre_cuenta__icontains=moneda_str)
    
    if cuentas_moneda.exists():
        return cuentas_moneda.first()
    
    if cuentas.exists():
        return cuentas.first()
        
    return None

@receiver(post_save, sender='finance.GastoOperativo')
def contabilizar_gasto_operativo(sender, instance, created, **kwargs):
    from apps.finance.models import GastoOperativo
    """
    Genera/Actualiza el Asiento Contable automáticamente.
    Asiento:
        DEBE: Cuenta de Gasto (instance.categoria)
        HABER: Cuenta de Caja/Banco (según metodo_pago)
    """
    if getattr(instance, '_skip_signal', False):
        return

    try:
        cuenta_haber = _get_cuenta_banco_caja(instance.metodo_pago, instance.moneda)
        if not cuenta_haber:
            logger.warning(f"No se encontró cuenta contable para pago {instance.metodo_pago} en {instance.moneda}")
            # Podríamos lanzar error, pero mejor dejar el asiento descuadrado o pendiente?
            # Por ahora retornamos
            return

        # Crear o Recuperar Asiento
        asiento = instance.asiento_contable
        if not asiento:
            asiento = AsientoContable.objects.create(
                fecha_contable=instance.fecha,
                descripcion_general=f"Gasto: {instance.descripcion}",
                tipo_asiento='DIA', # Diario / Egreso
                moneda=instance.moneda,
                referencia_documento=f"GASTO-{instance.pk}",
                estado='BOR' # Borrador por defecto
            )
            instance.asiento_contable = asiento
            # Guardamos sin disparar señal de nuevo para evitar loop recursivo if fields updated
            instance._skip_signal = True
            instance.save(update_fields=['asiento_contable'])
        else:
            # Actualizar cabecera
            asiento.fecha_contable = instance.fecha
            asiento.descripcion_general = f"Gasto: {instance.descripcion}"
            asiento.moneda = instance.moneda
            asiento.save()
            # Limpiar detalles anteriores para recrear
            asiento.detalles_asiento.all().delete()

        # CREAR DETALLES
        # 1. DEBE (Gasto)
        DetalleAsiento.objects.create(
            asiento=asiento,
            linea=1,
            cuenta_contable=instance.categoria,
            debe=instance.monto,
            haber=0,
            descripcion_linea=f"Cargo a {instance.categoria.nombre_cuenta}"
        )
        
        # 2. HABER (Salida de Dinero)
        DetalleAsiento.objects.create(
            asiento=asiento,
            linea=2,
            cuenta_contable=cuenta_haber,
            debe=0,
            haber=instance.monto,
            descripcion_linea=f"Pago con {instance.get_metodo_pago_display()}"
        )
        
        # Calcular totales
        asiento.calcular_totales()
        
    except Exception as e:
        logger.error(f"Error contabilizando Gasto #{instance.pk}: {e}")

@receiver(post_delete, sender='finance.GastoOperativo')
def eliminar_asiento_gasto(sender, instance, **kwargs):
    from apps.finance.models import GastoOperativo
    if instance.asiento_contable:
        instance.asiento_contable.delete()
