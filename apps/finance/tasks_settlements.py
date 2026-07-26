import logging
from decimal import Decimal

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Count, Sum
from django.utils import timezone

from apps.finance.models_stubs import ComisionVenta, LiquidacionAgente

logger = logging.getLogger(__name__)


@shared_task(
    name="apps.finance.tasks.generar_liquidaciones_mensuales_task",
    time_limit=600,
    soft_time_limit=540,
)
def generar_liquidaciones_mensuales_task(anio=None, mes=None, agencia_id=None):
    """generar_liquidaciones_mensuales_task."""
    from core.api import Agencia, agency_context

    referencia = timezone.now()
    if anio is None:
        anio = referencia.year
    if mes is None:
        if referencia.month == 1:
            mes = 12
            anio = anio - 1
        else:
            mes = referencia.month - 1

    logger.info(f"🏁 Iniciando cierre de mes para agentes: Periodo {mes}/{anio}")

    if agencia_id:
        agencias = [Agencia.objects.get(pk=agencia_id)]
    else:
        agencias = Agencia.objects.filter(activa=True).iterator(chunk_size=50)

    liquidaciones_creadas = 0

    for agencia in agencias:
        with agency_context(agencia):
            agentes_ids = (
                ComisionVenta.objects.filter(
                    estado=ComisionVenta.EstadoComision.PENDIENTE,
                    venta__agencia=agencia,
                )
                .values_list("agente_id", flat=True)
                .distinct()
            )

            for agente_id in agentes_ids:
                try:
                    with transaction.atomic():
                        comisiones_qs = ComisionVenta.objects.filter(
                            agente_id=agente_id,
                            estado=ComisionVenta.EstadoComision.PENDIENTE,
                            venta__agencia=agencia,
                        ).select_related("venta__agencia")

                        if not comisiones_qs.exists():
                            continue

                        agente = comisiones_qs.first().agente

                        totales = comisiones_qs.aggregate(
                            total=Sum("monto_comision"), cantidad=Count("id")
                        )

                        total_pagar = Decimal(str(totales["total"] or 0))
                        num_ventas = totales["cantidad"]

                        liquidacion, created = LiquidacionAgente.objects.get_or_create(
                            agente=agente,
                            periodo_mes=mes,
                            periodo_anio=anio,
                            defaults={
                                "agencia": agencia,
                                "total_comisiones": total_pagar,
                                "cantidad_ventas": num_ventas,
                            },
                        )

                        if not created:
                            liquidacion.total_comisiones += total_pagar
                            liquidacion.cantidad_ventas += num_ventas
                            liquidacion.save()

                        comisiones_qs.update(
                            estado=ComisionVenta.EstadoComision.LIQUIDADO,
                            fecha_liquidacion=timezone.now(),
                            liquidacion_asociada=liquidacion,
                        )

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
