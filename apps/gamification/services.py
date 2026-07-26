import logging

from django.db.models import Sum
from django.utils import timezone

logger = logging.getLogger(__name__)

REGISTRY = {}


def registrar_logro(codigo):
    """Decorator para registrar evaluadores de logros."""

    def decorator(fn):
        """decorator."""
        REGISTRY[codigo] = fn
        return fn

    return decorator


def evaluar_logros(agencia, usuario, evento, **kwargs):
    """Evalúa todos los logros que correspondan al evento."""
    from .models import Logro, LogroProgreso

    logros = Logro.objects.filter(activo=True)
    cambios = []

    for logro in logros:
        evaluator = REGISTRY.get(logro.codigo)
        if not evaluator:
            continue

        progreso, _ = LogroProgreso.objects.get_or_create(
            usuario=usuario,
            logro=logro,
            agencia=agencia,
        )
        if progreso.completado:
            continue

        try:
            nuevo_valor = evaluator(agencia, usuario, progreso, **kwargs)
        except Exception as e:
            logger.exception(f"Error evaluando logro {logro.codigo}: {e}")
            continue

        if nuevo_valor is not None and nuevo_valor != progreso.progreso:
            progreso.progreso = min(nuevo_valor, 100)
            if progreso.progreso >= 100:
                progreso.completado = True
                progreso.fecha_completado = timezone.now()
                cambios.append(logro)
            progreso.save()

    if cambios:
        _actualizar_puntuacion(agencia, usuario)

    return cambios


def _actualizar_puntuacion(agencia, usuario):
    """_actualizar_puntuacion."""
    from .models import LogroProgreso, Nivel, PuntuacionUsuario

    total_puntos = (
        LogroProgreso.objects.filter(usuario=usuario, agencia=agencia, completado=True).aggregate(
            total=Sum("logro__puntos")
        )["total"]
        or 0
    )
    completados = LogroProgreso.objects.filter(
        usuario=usuario, agencia=agencia, completado=True
    ).count()
    nivel = Nivel.objects.filter(puntos_minimos__lte=total_puntos).last()

    punt, _ = PuntuacionUsuario.objects.get_or_create(usuario=usuario, agencia=agencia)
    punt.puntos_total = total_puntos
    punt.nivel = nivel
    punt.logros_completados = completados
    punt.save()


def _count_ventas(agencia, usuario):
    """_count_ventas."""
    from apps.bookings.models import Venta

    return Venta.objects.filter(creado_por=usuario, agencia=agencia).count()


def _count_ventas_hoy(agencia, usuario):
    """_count_ventas_hoy."""
    from apps.bookings.models import Venta

    return Venta.objects.filter(
        creado_por=usuario,
        agencia=agencia,
        created_at__date=timezone.now().date(),
    ).count()


def _count_boletos(agencia, usuario):
    """_count_boletos."""
    from apps.bookings.models import BoletoImportado

    return BoletoImportado.objects.filter(importado_por=usuario, agencia=agencia).count()


def _count_clientes(agencia, usuario):
    """_count_clientes."""
    from apps.crm.models import Cliente

    return Cliente.objects.filter(creado_por=usuario, agencia=agencia).count()


def _count_articulos(agencia, usuario):
    """_count_articulos."""
    from apps.cms.models import Articulo

    return Articulo.objects.filter(creado_por=usuario, agencia=agencia).count()


def _count_pagos_confirmados(agencia, usuario):
    """_count_pagos_confirmados."""
    from apps.bookings.models import PagoVenta

    return PagoVenta.objects.filter(creado_por=usuario, agencia=agencia, confirmado=True).count()


def _count_integraciones(agencia, usuario):
    """_count_integraciones."""
    from core.models.webhook import Webhook

    return Webhook.objects.filter(agencia=agencia).count()


def _count_equipo(agencia, usuario):
    """_count_equipo."""
    from core.models.agencia import UsuarioAgencia

    return UsuarioAgencia.objects.filter(agencia=agencia).count()


def _check_primer_evento(agencia, usuario, progreso, **kwargs):
    """_check_primer_evento."""
    return 100 if kwargs.get("count", 0) > 0 else 0


@registrar_logro("primera_venta")
def evaluar_primera_venta(agencia, usuario, progreso, **kwargs):
    """evaluar_primera_venta."""
    if _count_ventas(agencia, usuario) >= 1:
        return 100
    return progreso.progreso


@registrar_logro("primer_boleto")
def evaluar_primer_boleto(agencia, usuario, progreso, **kwargs):
    """evaluar_primer_boleto."""
    if _count_boletos(agencia, usuario) >= 1:
        return 100
    return progreso.progreso


@registrar_logro("primer_cliente")
def evaluar_primer_cliente(agencia, usuario, progreso, **kwargs):
    """evaluar_primer_cliente."""
    if _count_clientes(agencia, usuario) >= 1:
        return 100
    return progreso.progreso


@registrar_logro("primer_pago")
def evaluar_primer_pago(agencia, usuario, progreso, **kwargs):
    """evaluar_primer_pago."""
    if _count_pagos_confirmados(agencia, usuario) >= 1:
        return 100
    return progreso.progreso


@registrar_logro("cinco_ventas")
def evaluar_cinco_ventas(agencia, usuario, progreso, **kwargs):
    """evaluar_cinco_ventas."""
    total = _count_ventas(agencia, usuario)
    return int((total / 5) * 100)


@registrar_logro("diez_ventas")
def evaluar_diez_ventas(agencia, usuario, progreso, **kwargs):
    """evaluar_diez_ventas."""
    total = _count_ventas(agencia, usuario)
    return int((total / 10) * 100)


@registrar_logro("cincuenta_ventas")
def evaluar_cincuenta_ventas(agencia, usuario, progreso, **kwargs):
    """evaluar_cincuenta_ventas."""
    total = _count_ventas(agencia, usuario)
    return int((total / 50) * 100)


@registrar_logro("ventas_hoy")
def evaluar_ventas_hoy(agencia, usuario, progreso, **kwargs):
    """evaluar_ventas_hoy."""
    total = _count_ventas_hoy(agencia, usuario)
    return int((total / 1) * 100)


@registrar_logro("diez_boletos")
def evaluar_diez_boletos(agencia, usuario, progreso, **kwargs):
    """evaluar_diez_boletos."""
    total = _count_boletos(agencia, usuario)
    return int((total / 10) * 100)


@registrar_logro("primer_articulo")
def evaluar_primer_articulo(agencia, usuario, progreso, **kwargs):
    """evaluar_primer_articulo."""
    if _count_articulos(agencia, usuario) >= 1:
        return 100
    return progreso.progreso


@registrar_logro("equipo_completo")
def evaluar_equipo_completo(agencia, usuario, progreso, **kwargs):
    """evaluar_equipo_completo."""
    total = _count_equipo(agencia, usuario)
    return int((total / 3) * 100)


@registrar_logro("integraciones_activas")
def evaluar_integraciones(agencia, usuario, progreso, **kwargs):
    """evaluar_integraciones."""
    total = _count_integraciones(agencia, usuario)
    return int((total / 1) * 100)
