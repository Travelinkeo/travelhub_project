"""Tests para core/security.py — helpers de tenant y permisos."""

import pytest

pytestmark = [pytest.mark.unit]


class TestFilterQuerysetByTenant:
    def test_returns_queryset_unchanged(self):
        from core.security import filter_queryset_by_tenant

        class FakeQuerySet:
            def filter(self, **kwargs):
                return kwargs

        result = filter_queryset_by_tenant(FakeQuerySet(), agencia_id=1)
        assert result == {"agencia_id": 1}

    def test_handles_none_agencia(self):
        from core.security import filter_queryset_by_tenant

        class FakeQuerySet:
            def filter(self, **kwargs):
                return kwargs

        result = filter_queryset_by_tenant(FakeQuerySet(), agencia_id=None)
        assert result == {}


class TestGetAgenciaFromRequest:
    def test_returns_none_without_request(self):
        from core.security import get_agencia_from_request

        assert get_agencia_from_request(None) is None

    def test_returns_none_without_user(self):
        from core.security import get_agencia_from_request

        class FakeRequest:
            user = None

        assert get_agencia_from_request(FakeRequest()) is None


class TestGetAgenciaOr403:
    def test_returns_agencia_from_request(self, monkeypatch):
        from core.security import get_agencia_or_403

        fake_agencia = object()
        monkeypatch.setattr(
            "core.security.get_agencia_from_request",
            lambda req: fake_agencia,
        )

        result = get_agencia_or_403("mock_request")
        assert result is fake_agencia
