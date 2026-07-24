"""
Conftest de plugins — fixtures de mock que deben estar disponibles
globalmente para toda la suite de tests.

Cada fixture aquí debería ser autouse=False (activación explícita)
a menos que genuinamente deba aplicarse a todos los tests.
"""

import json
import unittest.mock

import pytest


@pytest.fixture
def mock_responses():
    """Fixture que envuelve la librería `responses` para mockear HTTP.

    Uso:
        def test_external_api(mock_responses):
            mock_responses.add(
                responses.GET,
                "https://api.example.com/endpoint",
                json={"status": "ok"},
                status=200,
            )
            # requests.get("https://api.example.com/endpoint") ahora retorna el mock
    """
    import responses

    with responses.RequestsMock() as rsps:
        yield rsps


@pytest.fixture
def vcr_cassette(request):
    """Fixture condicional que aplica VCR si el test tiene el marker @pytest.mark.vcr.

    Uso:
        @pytest.mark.vcr
        def test_with_real_api():
            # responses se graban/reproducen desde tests/cassettes/
            response = requests.get("https://api.example.com")
    """
    marker = request.node.get_closest_marker("vcr")
    if marker:
        import vcr as _vcr

        cassette_library_dir = request.config.rootpath / "tests" / "cassettes"
        cassette_library_dir.mkdir(parents=True, exist_ok=True)

        cassette_name = f"{request.node.module.__name__}.{request.node.name}.yaml"

        my_vcr = _vcr.VCR(
            cassette_library_dir=str(cassette_library_dir),
            path_transformer=_vcr.VCR.ensure_suffix(".yaml"),
            record_mode="once",
            filter_headers=["authorization", "Authorization", "x-api-key", "X-API-Key"],
            filter_query_parameters=["api_key", "key", "token", "secret"],
        )

        with my_vcr.use_cassette(cassette_name):
            yield
    else:
        yield
