"""Servicio de freelancer service para la aplicación crm.
"""

import logging
from decimal import Decimal

from django.db.models import Sum

logger = logging.getLogger(__name__)


class FreelancerService:
    """
    Servicio para gestionar comisiones y saldos de freelancers.
    """

    @staticmethod
    def calculate_commission(venta) -> None:
        """
        Calcula y guarda la comisión asignada a un freelancer para una venta dada,
        si el creador de la venta tiene un perfil de freelancer activo.
        """
        if not venta.creado_por:
            logger.debug(f"Venta {venta.pk} no tiene creado_por. Ignorando cálculo de comisión.")
            return

        from apps.crm.models import ComisionFreelancer, FreelancerProfile

        try:
            # Buscar perfil del freelancer asociado al creador de la venta
            freelancer = FreelancerProfile.objects.filter(
                usuario=venta.creado_por, agencia=venta.agencia, activo=True
            ).first()
        except Exception as e:
            logger.error(
                f"Error buscando FreelancerProfile para el usuario {venta.creado_por}: {e}"
            )
            return

        if not freelancer:
            logger.debug(
                f"El creador de la venta {venta.creado_por.username} no es un freelancer activo."
            )
            return

        # 1. Calcular comisión basada en porcentaje del markup bruto (utilidad)
        markup = venta.markup_bruto or Decimal("0.00")
        if markup < 0:
            markup = Decimal("0.00")

        porcentaje = freelancer.porcentaje_comision or Decimal("0.00")
        comision_variable = markup * (porcentaje / Decimal("100.00"))

        # 2. Calcular comisión fija por boletos adjuntos
        comision_fija_total = Decimal("0.00")
        fija_por_boleto = freelancer.comision_fija_por_boleto or Decimal("0.00")
        if fija_por_boleto > 0:
            boletos_count = venta.boletos_adjuntos.count()
            comision_fija_total = fija_por_boleto * Decimal(boletos_count)

        total_comision = comision_variable + comision_fija_total

        # 3. Crear o actualizar ComisionFreelancer
        comision, created = ComisionFreelancer.objects.get_or_create(
            venta=venta,
            defaults={
                "freelancer": freelancer,
                "agencia": venta.agencia,
                "monto_base_venta": markup,
                "monto_comision_ganada": total_comision,
                "liquidada": False,
            },
        )

        if not created:
            # Solo actualizamos el cálculo si no ha sido liquidada todavía
            if not comision.liquidada:
                comision.monto_base_venta = markup
                comision.monto_comision_ganada = total_comision
                comision.save(update_fields=["monto_base_venta", "monto_comision_ganada"])
                logger.info(f"Comisión actualizada para venta {venta.pk}: {total_comision}")
        else:
            logger.info(f"Nueva comisión generada para venta {venta.pk}: {total_comision}")

        # Recalcular saldos del freelancer
        FreelancerService.recalculate_balances(freelancer)

    @staticmethod
    def recalculate_balances(freelancer) -> None:
        """
        Recalcula el saldo por cobrar y el total histórico pagado de un freelancer.
        """
        # Sumar comisiones no liquidadas
        saldo_no_liquidado = freelancer.comisiones_generadas.filter(
            liquidada=False, is_deleted=False
        ).aggregate(total=Sum("monto_comision_ganada"))["total"] or Decimal("0.00")

        # Sumar comisiones liquidadas
        total_pagado = freelancer.comisiones_generadas.filter(
            liquidada=True, is_deleted=False
        ).aggregate(total=Sum("monto_comision_ganada"))["total"] or Decimal("0.00")

        # Guardar en base de datos
        freelancer.saldo_por_cobrar = saldo_no_liquidado
        freelancer.total_historico_pagado = total_pagado
        freelancer.save(update_fields=["saldo_por_cobrar", "total_historico_pagado"])
        logger.info(
            f"Balances actualizados para freelancer {freelancer.usuario.username}: "
            f"Saldo por cobrar={saldo_no_liquidado}, Total pagado={total_pagado}"
        )
