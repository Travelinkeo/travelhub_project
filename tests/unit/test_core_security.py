import pytest
from django.core.exceptions import PermissionDenied

pytestmark = [pytest.mark.unit]


class TestFilterQuerysetByTenant:
    def test_filters_by_agencia(self):
        from core.security import filter_queryset_by_tenant

        calls = []

        class FakeQS:
            def filter(self, **kwargs):
                calls.append(kwargs)
                return self

        result = filter_queryset_by_tenant(FakeQS(), agencia="agencia_obj")
        assert result is not None
        assert calls == [{"agencia": "agencia_obj"}]

    def test_skips_filter_when_agencia_none(self):
        from core.security import filter_queryset_by_tenant

        called = False

        class FakeQS:
            def filter(self, **kwargs):
                nonlocal called
                called = True
                return self

        filter_queryset_by_tenant(FakeQS(), agencia=None)
        assert called is False


class TestGetAgenciaFromRequest:
    def test_raises_for_none_request(self):
        from core.security import get_agencia_from_request

        with pytest.raises(AttributeError):
            get_agencia_from_request(None)

    def test_raises_for_none_user(self):
        from core.security import get_agencia_from_request

        class FakeRequest:
            user = None

        with pytest.raises(AttributeError):
            get_agencia_from_request(FakeRequest())

    def test_raises_for_unauthenticated_user(self, rf):
        from django.contrib.auth.models import AnonymousUser

        from core.security import get_agencia_from_request

        req = rf.get("/")
        req.user = AnonymousUser()
        with pytest.raises(PermissionDenied, match="Autenticación requerida"):
            get_agencia_from_request(req)

    def test_returns_none_for_superuser(self, rf, db):
        from django.contrib.auth import get_user_model

        from core.security import get_agencia_from_request

        User = get_user_model()
        user = User.objects.create(is_superuser=True, username="admin")
        req = rf.get("/")
        req.user = user
        result = get_agencia_from_request(req)
        assert result is None

    def test_raises_for_user_without_agencia(self, rf, monkeypatch):
        from core.security import get_agencia_from_request

        user = type("FakeUser", (), {"is_authenticated": True, "is_superuser": False})()
        monkeypatch.setattr("core.security.get_user_active_agency", lambda u: None)
        req = rf.get("/")
        req.user = user
        with pytest.raises(PermissionDenied, match="agencia activa"):
            get_agencia_from_request(req)


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
