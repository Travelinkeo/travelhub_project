import logging
import os

from django.http import Http404

logger = logging.getLogger(__name__)


class MultiTenantDomainMiddleware:
    """Middleware de enrutamiento avanzado para resolver inquilinos (tenants)."""

    def __init__(self, get_response):
        """__init__."""
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host().split(":")[0].lower()
        main_domain = os.getenv("MAIN_DOMAIN", "travelhub.cc").lower()

        global_hosts = ["localhost", "127.0.0.1", "testserver", main_domain, f"www.{main_domain}"]
        if host in global_hosts:
            request.agencia = None
            request.agency = None
            return self.get_response(request)

        from core.models.agencia import Agencia

        agencia = Agencia.objects.filter(dominio_personalizado=host, activa=True).first()

        if not agencia:
            subdomain = None
            if host.endswith(f".{main_domain}"):
                subdomain = host.replace(f".{main_domain}", "")
            elif host.endswith(".localhost"):
                subdomain = host.replace(".localhost", "")

            if subdomain:
                agencia = Agencia.objects.filter(
                    configuracion_v2__subdominio_slug=subdomain, activa=True
                ).first()

        if agencia:
            request.agencia = agencia
            request.agency = agencia
            return self.get_response(request)

        raise Http404(
            "La plataforma solicitada no existe, no está activa o tiene problemas de configuración."
        )
