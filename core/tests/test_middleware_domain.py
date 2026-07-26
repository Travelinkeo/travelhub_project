# core/tests/test_middleware_domain.py
import pytest
from django.http import Http404
from django.test import RequestFactory, override_settings

from core.middleware import MultiTenantDomainMiddleware


def mock_get_response(request):
    """mock_get_response."""
    return "response"


@pytest.mark.django_db
@override_settings(ALLOWED_HOSTS=["*"])
def test_multitenant_domain_middleware_global_hosts():
    """test_multitenant_domain_middleware_global_hosts."""
    factory = RequestFactory()
    middleware = MultiTenantDomainMiddleware(mock_get_response)

    # Pruebas con hosts globales (deberían saltarse la resolución y procesar normalmente)
    for host in ["localhost", "127.0.0.1", "travelhub.cc", "www.travelhub.cc", "testserver"]:
        request = factory.get("/", HTTP_HOST=host)
        response = middleware(request)
        assert response == "response"
        assert getattr(request, "agencia", None) is None


@pytest.mark.django_db
@override_settings(ALLOWED_HOSTS=["*"])
def test_multitenant_domain_middleware_custom_domain(agencia):
    """test_multitenant_domain_middleware_custom_domain."""
    # Asignar dominio personalizado a la agencia de prueba
    agencia.dominio_personalizado = "viajes.humboldt.com"
    agencia.save()

    factory = RequestFactory()
    middleware = MultiTenantDomainMiddleware(mock_get_response)

    request = factory.get("/", HTTP_HOST="viajes.humboldt.com")
    response = middleware(request)
    assert response == "response"
    assert request.agencia == agencia


@pytest.mark.django_db
@override_settings(ALLOWED_HOSTS=["*"])
def test_multitenant_domain_middleware_subdomain(agencia):
    """test_multitenant_domain_middleware_subdomain."""
    # Registrar el subdominio en la configuración de la agencia
    config = agencia.configuracion
    config.subdominio_slug = "humboldt"
    config.save()

    factory = RequestFactory()
    middleware = MultiTenantDomainMiddleware(mock_get_response)

    # Caso 1: En producción (humboldt.travelhub.cc)
    request = factory.get("/", HTTP_HOST="humboldt.travelhub.cc")
    response = middleware(request)
    assert response == "response"
    assert request.agencia == agencia

    # Caso 2: En desarrollo local (humboldt.localhost)
    request2 = factory.get("/", HTTP_HOST="humboldt.localhost")
    response2 = middleware(request2)
    assert response2 == "response"
    assert request2.agencia == agencia


@pytest.mark.django_db
@override_settings(ALLOWED_HOSTS=["*"])
def test_multitenant_domain_middleware_unregistered_domain():
    """test_multitenant_domain_middleware_unregistered_domain."""
    factory = RequestFactory()
    middleware = MultiTenantDomainMiddleware(mock_get_response)

    # Debería elevar un Http404 al intentar resolver un host desconocido que no es global ni subdominio base
    with pytest.raises(Http404):
        request = factory.get("/", HTTP_HOST="dominio-no-registrado.com")
        middleware(request)
