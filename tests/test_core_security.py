"""Tests para core/security.py — capa de seguridad multi-tenant."""

from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.http import Http404

from core.middleware import agency_var
from core.models import Agencia, UsuarioAgencia
from core.security import (
    agency_role_required,
    filter_queryset_by_tenant,
    get_agencia_from_request,
    get_object_tenant_or_404,
    get_user_active_agency,
    invalidate_all_agency_caches,
    invalidate_user_agencia_cache,
)

User = get_user_model()
pytestmark = pytest.mark.django_db


class TestGetUserActiveAgency:
    def test_return_none_si_no_autenticado(self):
        user = AnonymousUser()
        assert get_user_active_agency(user) is None

    def test_return_none_sin_relation_manager(self):
        user = User.objects.create_user(username="test_no_rel", password="pw")
        assert get_user_active_agency(user) is None

    def test_prioridad_agency_var(self, agencia_premium):
        user = User.objects.create_user(username="test", password="pw")
        UsuarioAgencia.objects.create(usuario=user, agencia=agencia_premium, rol="vendedor")
        token = agency_var.set(agencia_premium)
        try:
            result = get_user_active_agency(user)
            assert result == agencia_premium
        finally:
            agency_var.reset(token)

    def test_cache_miss_fallback_db(self, agencia_premium):
        user = User.objects.create_user(username="test2", password="pw")
        UsuarioAgencia.objects.create(usuario=user, agencia=agencia_premium, rol="vendedor")
        with patch("django.core.cache.cache.get", return_value=None):
            result = get_user_active_agency(user)
            assert result == agencia_premium

    def test_cache_golpe_devuelve_agencia(self, agencia_premium):
        user = User.objects.create_user(username="test3", password="pw")
        with patch("django.core.cache.cache.get", return_value=agencia_premium.pk):
            result = get_user_active_agency(user)
            assert result == agencia_premium

    def test_cache_golpe_none_retorna_none(self):
        user = User.objects.create_user(username="test4", password="pw")
        with patch("django.core.cache.cache.get", return_value="none"):
            result = get_user_active_agency(user)
            assert result is None

    def test_sin_usuariouser_agencia_retorna_none(self):
        user = User.objects.create_user(username="orphan", password="pw")
        result = get_user_active_agency(user)
        assert result is None

    def test_cache_invalidate(self, agencia_premium):
        user = User.objects.create_user(username="test5", password="pw")
        UsuarioAgencia.objects.create(usuario=user, agencia=agencia_premium, rol="admin")
        result = get_user_active_agency(user)
        assert result == agencia_premium
        invalidate_user_agencia_cache(user.pk)
        with patch("django.core.cache.cache.get", return_value=None):
            result2 = get_user_active_agency(user)
            assert result2 == agencia_premium


class TestInvalidateCaches:
    def test_invalidate_all_agency_caches(self, agencia_premium):
        users = []
        for i in range(3):
            u = User.objects.create_user(username=f"inval_{i}", password="pw")
            UsuarioAgencia.objects.create(usuario=u, agencia=agencia_premium, rol="vendedor")
            users.append(u)
        for u in users:
            get_user_active_agency(u)
        invalidate_all_agency_caches(agencia_premium.pk)
        for u in users:
            with patch("django.core.cache.cache.get", return_value=None):
                result = get_user_active_agency(u)
                assert result == agencia_premium


class TestGetAgenciaFromRequest:
    def test_anonimo_raise(self):
        req = type("Req", (), {"user": AnonymousUser()})
        with pytest.raises(PermissionDenied, match="Autenticaci"):
            get_agencia_from_request(req)

    def test_superuser_retorna_none(self):
        user = User.objects.create_user(
            username="su", password="pw", is_superuser=True
        )
        req = type("Req", (), {"user": user})
        assert get_agencia_from_request(req) is None

    def test_sin_agencia_raise(self):
        user = User.objects.create_user(username="sinagencia", password="pw")
        req = type("Req", (), {"user": user})
        with pytest.raises(PermissionDenied, match="agencia activa"):
            get_agencia_from_request(req)

    def test_con_agencia_retorna(self, agencia_premium):
        user = User.objects.create_user(username="conagencia", password="pw")
        UsuarioAgencia.objects.create(usuario=user, agencia=agencia_premium, rol="admin")
        req = type("Req", (), {"user": user})
        result = get_agencia_from_request(req)
        assert result == agencia_premium


class TestGetObjectTenantOr404:
    def test_superuser_sin_filtro(self, agencia_premium):
        from apps.bookings.models import Venta
        from apps.finance.models import Moneda

        moneda = Moneda.objects.create(codigo_iso="USD", nombre="Dolar", simbolo="$")
        venta = Venta.objects.create(agencia=agencia_premium, moneda=moneda, total_venta=100)
        result = get_object_tenant_or_404(Venta, None, pk=venta.pk)
        assert result == venta

    def test_filtra_por_agencia(self, agencia_premium, agencia_estandar):
        from apps.bookings.models import Venta
        from apps.finance.models import Moneda

        moneda = Moneda.objects.create(codigo_iso="USD", nombre="Dolar", simbolo="$")
        venta_a = Venta.objects.create(agencia=agencia_premium, moneda=moneda, total_venta=100)
        Venta.objects.create(agencia=agencia_estandar, moneda=moneda, total_venta=200)
        with pytest.raises(Http404):
            get_object_tenant_or_404(Venta, agencia_premium, pk=venta_a.pk + 1)

    def test_objeto_no_existe_404(self):
        with pytest.raises(Http404):
            get_object_tenant_or_404(Agencia, None, pk=99999)


class TestFilterQuerysetByTenant:
    def test_superuser_sin_filtro(self, agencia_premium, agencia_estandar):
        from apps.finance.models import Moneda

        Moneda.objects.create(codigo_iso="USD", nombre="Dolar", simbolo="$")
        Moneda.objects.create(codigo_iso="EUR", nombre="Euro", simbolo="€")
        qs = Moneda.objects.all()
        result = filter_queryset_by_tenant(qs, None)
        assert result.count() >= 2

    def test_filtra_por_agencia(self, agencia_premium, agencia_estandar):
        from apps.bookings.models import Venta
        from apps.finance.models import Moneda

        moneda = Moneda.objects.create(codigo_iso="USD", nombre="Dolar", simbolo="$")
        Venta.objects.create(agencia=agencia_premium, moneda=moneda, total_venta=100)
        Venta.objects.create(agencia=agencia_estandar, moneda=moneda, total_venta=200)
        qs = Venta.objects.all()
        result = filter_queryset_by_tenant(qs, agencia_premium)
        assert result.count() == 1


class TestAgencyRoleRequired:
    def test_anonimo_raise(self):
        req = type("Req", (), {"user": AnonymousUser()})
        decorator = agency_role_required(["admin"])
        with pytest.raises(PermissionDenied):
            decorator(lambda r: "ok")(req)

    def test_superuser_bypass(self):
        user = User.objects.create_user(
            username="su_bypass", password="pw", is_superuser=True
        )
        req = type("Req", (), {"user": user})
        decorator = agency_role_required(["admin"])
        result = decorator(lambda r: "ok")(req)
        assert result == "ok"

    def test_rol_permitido(self, agencia_premium):
        user = User.objects.create_user(username="admin_user", password="pw")
        UsuarioAgencia.objects.create(usuario=user, agencia=agencia_premium, rol="admin")
        req = type("Req", (), {"user": user})
        decorator = agency_role_required(["admin", "gerente"])
        result = decorator(lambda r: "granted")(req)
        assert result == "granted"

    def test_rol_denegado_raise(self, agencia_premium):
        user = User.objects.create_user(username="vendedor_noop", password="pw")
        UsuarioAgencia.objects.create(usuario=user, agencia=agencia_premium, rol="vendedor")
        req = type("Req", (), {"user": user})
        decorator = agency_role_required(["admin", "gerente"])
        with pytest.raises(PermissionDenied):
            decorator(lambda r: "nope")(req)
