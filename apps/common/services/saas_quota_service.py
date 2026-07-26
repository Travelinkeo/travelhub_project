import logging

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)


class SaaSQuotaService:
    """
    Servicio centralizado para la gestión y cumplimiento de cuotas SaaS.
    Utiliza Redis para evitar hits constantes a la base de datos.
    """

    CACHE_TTL = 3600  # 1 hora por defecto

    @classmethod
    def get_limits(cls, agencia):
        plan = getattr(agencia, "plan", "FREE")
        return settings.SAAS_PLAN_LIMITS.get(plan, settings.SAAS_PLAN_LIMITS["FREE"])

    @classmethod
    def check_quota(cls, agencia, resource_type):
        """
        Verifica si la agencia ha excedido su cuota para un recurso específico.
        """
        if not agencia:
            return True

        plan = agencia.plan
        limits = settings.SAAS_PLAN_LIMITS.get(plan, settings.SAAS_PLAN_LIMITS["FREE"])
        limit = limits.get(resource_type)

        if limit is None or limit >= 999:
            return True

        current_usage = cls.get_current_usage(agencia, resource_type)

        if current_usage >= limit:
            logger.warning(
                f"🚨 Cuota excedida para {agencia.nombre}: {resource_type} ({current_usage}/{limit})"
            )
            return False

        return True

    @classmethod
    def get_current_usage(cls, agencia, resource_type):
        """
        Obtiene el uso actual de un recurso, consultando Redis primero.
        """
        current_month = timezone.now().strftime("%Y-%m")
        cache_key = f"quota_{agencia.id}_{resource_type}_{current_month}"
        usage = cache.get(cache_key)

        if usage is None:
            usage = cls._fetch_usage_from_db(agencia, resource_type)
            # Usar cache.add (SETNX) para evitar race condition entre hilos
            if not cache.add(cache_key, usage, timeout=2592000):
                usage = cache.get(cache_key)

        return usage

    @classmethod
    def _fetch_usage_from_db(cls, agencia, resource_type):
        """
        Consulta la base de datos para obtener el conteo real del mes en curso.
        """
        now = timezone.now()
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        try:
            if resource_type == "sales_per_month":
                from django.apps import apps

                Venta = apps.get_model("bookings", "Venta")

                return Venta.objects.filter(
                    agencia_id=agencia.id, fecha_venta__gte=start_of_month
                ).count()

            if resource_type == "leads_per_month":
                from django.apps import apps

                Cotizacion = apps.get_model("cotizaciones", "Cotizacion")
                OportunidadViaje = apps.get_model("crm", "OportunidadViaje")

                ops = OportunidadViaje.objects.filter(
                    agencia_id=agencia.id, creado_en__gte=start_of_month
                ).count()
                cots = Cotizacion.objects.filter(
                    agencia_id=agencia.id, fecha_emision__gte=start_of_month
                ).count()
                return ops + cots

            if resource_type == "users":
                return agencia.usuarios.filter(is_active=True).count()

        except Exception as e:
            logger.error(f"Error al contar recursos {resource_type} para agencia {agencia.id}: {e}")

        return 0

    @classmethod
    def increment_usage(cls, agencia_id, resource_type):
        """
        Incrementa el contador en caché tras una creación exitosa.
        """
        current_month = timezone.now().strftime("%Y-%m")
        cache_key = f"quota_{agencia_id}_{resource_type}_{current_month}"
        try:
            cache.incr(cache_key)
        except (ValueError, TypeError):
            # Si no existe, se recalculará en el próximo GET
            pass
