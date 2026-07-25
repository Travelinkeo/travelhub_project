"""Tests para Smoke imports."""
import importlib


def test_import_asgi_wsgi():
    """Import asgi wsgi."""
    asgi = importlib.import_module("travelhub.asgi")
    wsgi = importlib.import_module("travelhub.wsgi")
    assert hasattr(asgi, "application")
    assert hasattr(wsgi, "application")
