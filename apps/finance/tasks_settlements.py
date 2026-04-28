import logging
from django.db import transaction
from django.utils import timezone
from django.conf import settings
from django.db.models import Sum, Count
from celery import shared_task
from decimal import Decimal

from apps.finance.models.commissions import ComisionVenta, LiquidacionAgente
from django.core.mail import send_mail

logger = logging.getLogger(__name__)

@shared_task(name='apps.finance.tasks.generar_liquidaciones_mensuales_task')
def generar_liquidaciones_mensuales_task(anio=None, mes=None):
    """
    TAREA DE CIERRE DE MES AUTOMÁTICO PARA AGENTES:
    Agrupa comisiones pendientes, genera el recibo de pago y 
    notifica al agente por correo electrónico.
    """
    # 1. Determinar el periodo (Mes anterior por defecto si es día 1)
    referencia = timezone.now()
    if anio is None: anio = referencia.year
    if mes is None:
        # Si hoy es Enero, el mes anterior fue Diciembre del año pasado
        if referencia.month == 1:
            mes = 12
            anio = anio - 1
        else:
            mes = referencia.month - 1

    logger.info(f"🏁 Iniciando cierre de mes para agentes: Periodo {mes}/{anio}")

    # 2. Buscar Agentes con Comisiones PENDIENTES
    agentes_ids = ComisionVenta.objects.filter(
        estado=ComisionVenta.EstadoComision.PENDIENTE
    ).values_list('agente_id', flat=True).distinct()

    if not agentes_ids:
        logger.info("No hay comisiones pendientes para liquidar en este periodo.")
        return False

    liquidaciones_creadas = 0

    for agente_id in agentes_ids:
        try:
            with transaction.atomic():
                # 3. EXTRAER COMISIONES DEL AGENTE
                comisiones_qs = ComisionVenta.objects.filter(
                    agente_id=agente_id,
                    estado=ComisionVenta.EstadoComision.PENDIENTE
                ).select_related('venta__agencia')

                if not comisiones_qs.exists():
                    continue

                agencia = comisiones_qs.first().venta.agencia
                agente = comisiones_qs.first().agente

                # 4. Calcular Totales del Mes
                totales = comisiones_qs.aggregate(
                    total=Sum('monto_comision'),
                    cantidad=Count('id')
                )

                total_pagar = Decimal(str(totales['total'] or 0))
                num_ventas = totales['cantidad']

                # 5. Generar Liquidación Agente (Consolidado)
                liquidacion, created = LiquidacionAgente.objects.get_or_create(
                    agente=agente,
                    periodo_mes=mes,
                    periodo_anio=anio,
                    defaults={
                        'agencia': agencia,
                        'total_comisiones': total_pagar,
                        'cantidad_ventas': num_ventas
                    }
                )

                if not created:
                    # Si ya existía, actualizamos totales para este cierre
                    liquidacion.total_comisiones += total_pagar
                    liquidacion.cantidad_ventas += num_ventas
                    liquidacion.save()

                # 6. Vincular y marcar como LIQUIDADO (Blindaje)
                comisiones_qs.update(
                    estado=ComisionVenta.EstadoComision.LIQUIDADO,
                    fecha_liquidacion=timezone.now(),
                    liquidacion_asociada=liquidacion
                )

                # 7. Notificación al Agente
                try:
                    asunto = f"🚀 Liquidación de Comisiones TravelHub: {mes}/{anio}"
                    mensaje = f"""
                    Hola {agente.username},
                    
                    Tu estado de cuenta de este mes está listo.
                    Consolidado: ${total_pagar}
                    Ventas procesadas: {num_ventas}
                    
                    Puedes revisar el detalle descargando el PDF desde tu portal de agente.
                    Gracias por tu excelente desempeño en {agencia.nombre}.
                    """
                    send_mail(asunto, mensaje, settings.DEFAULT_FROM_EMAIL, [agente.email])
                    logger.info(f"📧 Notificación enviada a {agente.email}")

                except Exception as e:
                    logger.error(f"Fallo al enviar correo a {agente.email}: {e}")

                liquidaciones_creadas += 1

        except Exception as e:
            logger.exception(f"Error liquidando al agente {agente_id}: {e}")

    logger.info(f"✅ Proceso completo: {liquidaciones_creadas} agentes liquidados exitosamente.")
    return True
