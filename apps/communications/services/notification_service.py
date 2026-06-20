"""
Notification Service (In-App)
Creates in-app notifications (NotificacionInteligente / NotificacionAgente)
for sale events, state changes, and other CRM events.
"""

import logging

from django.contrib.auth.models import User
from django.utils import timezone

logger = logging.getLogger(__name__)


def _get_admin_users(agencia):
    """Get admin users for an agency to receive in-app notifications"""
    if not agencia:
        return User.objects.filter(is_staff=True, is_active=True)[:5]
    from apps.common.models import UserProfile

    profiles = UserProfile.objects.filter(
        agencia=agencia, role__in=["ADMIN", "GERENTE", "AGENTE"]
    ).select_related("user")
    return [p.user for p in profiles if p.user.is_active]


def notificar_confirmacion_venta(venta):
    """Create in-app notification when a sale is created"""
    try:
        from apps.automation.models import NotificacionInteligente

        users = _get_admin_users(venta.agencia)
        cliente_nombre = (
            venta.cliente.get_nombre_completo() if venta.cliente else "N/A"
        )

        for user in users:
            NotificacionInteligente.objects.create(
                usuario=user,
                tipo=NotificacionInteligente.Tipo.SUCCESS,
                titulo="Nueva Venta Creada",
                mensaje=(
                    f"Se ha creado una nueva venta #{venta.localizador or venta.pk} "
                    f"para el cliente {cliente_nombre} por {venta.moneda} {venta.total_venta:.2f}."
                ),
                ahorro_tiempo="",
            )

        logger.info(f"In-app notification: venta {venta.pk} created")
    except Exception as e:
        logger.warning(f"Error creating in-app notification for venta {venta.pk}: {e}")


def notificar_cambio_estado(venta, estado_anterior):
    """Create in-app notification when a sale changes state"""
    try:
        from apps.automation.models import NotificacionInteligente

        users = _get_admin_users(venta.agencia)
        cliente_nombre = (
            venta.cliente.get_nombre_completo() if venta.cliente else "N/A"
        )

        for user in users:
            NotificacionInteligente.objects.create(
                usuario=user,
                tipo=NotificacionInteligente.Tipo.INFO,
                titulo="Estado de Venta Actualizado",
                mensaje=(
                    f"La venta #{venta.localizador or venta.pk} ({cliente_nombre}) "
                    f"cambió de '{estado_anterior}' a '{venta.get_estado_display()}'."
                ),
                ahorro_tiempo="",
            )

        logger.info(f"In-app notification: venta {venta.pk} state changed to {venta.get_estado_display()}")
    except Exception as e:
        logger.warning(f"Error creating in-app notification for venta {venta.pk}: {e}")


def notificar_boleto_requiere_revision(boleto):
    """Create in-app notification when a ticket needs manual review"""
    try:
        from apps.automation.models import NotificacionInteligente

        users = _get_admin_users(boleto.agencia)

        for user in users:
            NotificacionInteligente.objects.create(
                usuario=user,
                tipo=NotificacionInteligente.Tipo.WARNING,
                titulo="Boleto Requiere Revisión",
                mensaje=(
                    f"El boleto #{boleto.pk} (PNR: {boleto.localizador_pnr or 'N/A'}) "
                    f"requiere revisión manual. Datos incompletos detectados."
                ),
                ahorro_tiempo="",
            )

        logger.info(f"In-app notification: boleto {boleto.pk} needs review")
    except Exception as e:
        logger.warning(f"Error creating in-app notification for boleto {boleto.pk}: {e}")


def notificar_pago_recibido(pago):
    """Create in-app notification when a payment is received"""
    try:
        from apps.automation.models import NotificacionInteligente

        venta = pago.venta
        users = _get_admin_users(venta.agencia if venta else None)
        cliente_nombre = (
            venta.cliente.get_nombre_completo() if venta and venta.cliente else "N/A"
        )

        for user in users:
            NotificacionInteligente.objects.create(
                usuario=user,
                tipo=NotificacionInteligente.Tipo.SUCCESS,
                titulo="Pago Recibido",
                mensaje=(
                    f"Se ha registrado un pago de {pago.moneda} {pago.monto:.2f} "
                    f"para la venta #{venta.localizador or venta.pk} del cliente {cliente_nombre}."
                ),
                ahorro_tiempo="",
            )

        logger.info(f"In-app notification: payment {pago.pk} received for venta {venta.pk}")
    except Exception as e:
        logger.warning(f"Error creating in-app notification for pago {pago.pk}: {e}")
