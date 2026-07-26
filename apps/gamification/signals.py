import logging

from django.db.models.signals import post_save
from django.dispatch import Signal, receiver

from core.middleware import get_current_agency, get_current_user

logger = logging.getLogger(__name__)

gamification_event = Signal()


@receiver(post_save, sender="bookings.Venta")
def on_venta_creada(sender, instance, created, **kwargs):
    """on_venta_creada."""
    if not created:
        return
    _disparar(instance.agencia, instance.creado_por, evento="venta_creada")


@receiver(post_save, sender="bookings.BoletoImportado")
def on_boleto_importado(sender, instance, created, **kwargs):
    """on_boleto_importado."""
    if not created:
        return
    _disparar(instance.agencia, instance.importado_por, evento="boleto_importado")


@receiver(post_save, sender="crm.Cliente")
def on_cliente_creado(sender, instance, created, **kwargs):
    """on_cliente_creado."""
    if not created:
        return
    _disparar(instance.agencia, instance.creado_por, evento="cliente_creado")


@receiver(post_save, sender="bookings.PagoVenta")
def on_pago_confirmado(sender, instance, created, **kwargs):
    """on_pago_confirmado."""
    if not created or not instance.confirmado:
        return
    _disparar(instance.agencia, instance.creado_por, evento="pago_confirmado")


@receiver(post_save, sender="cms.Articulo")
def on_articulo_creado(sender, instance, created, **kwargs):
    """on_articulo_creado."""
    if not created:
        return
    agencia = getattr(instance, "agencia", None) or get_current_agency()
    creado_por = getattr(instance, "creado_por", None) or get_current_user()
    _disparar(agencia, creado_por, evento="articulo_creado")


@receiver(post_save, sender="core.Webhook")
def on_webhook_creado(sender, instance, created, **kwargs):
    """on_webhook_creado."""
    if not created:
        return
    _disparar(instance.agencia, get_current_user(), evento="webhook_creado")


@receiver(post_save, sender="core.UsuarioAgencia")
def on_usuario_agregado(sender, instance, created, **kwargs):
    """on_usuario_agregado."""
    if not created:
        return
    _disparar(instance.agencia, instance.usuario, evento="usuario_agregado")


def _disparar(agencia, usuario, evento):
    """_disparar."""
    if not agencia or not usuario:
        return
    try:
        from .services import evaluar_logros

        logros_completados = evaluar_logros(agencia, usuario, evento=evento)
        if logros_completados:
            gamification_event.send(
                sender=None,
                agencia=agencia,
                usuario=usuario,
                logros=logros_completados,
            )
    except Exception as e:
        logger.exception(f"Error en gamificación para {evento}: {e}")
