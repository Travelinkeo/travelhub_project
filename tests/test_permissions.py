import pytest
from django.contrib.auth.models import Group, User
from django.core.exceptions import PermissionDenied
from rest_framework.test import APIRequestFactory

from core.permissions import IsStaffOrGroupWrite, rol_requerido


@pytest.mark.django_db
def test_is_staff_or_group_write_denies_anonymous():
    factory = APIRequestFactory()
    request = factory.get("/")
    request.user = type("Anon", (), {"is_authenticated": False})()
    perm = IsStaffOrGroupWrite()
    assert perm.has_permission(request, view=None) is False


@pytest.mark.django_db
def test_is_staff_or_group_write_allows_safe_authenticated():
    factory = APIRequestFactory()
    user = User.objects.create_user(username="alice", password="pwd")
    request = factory.get("/")
    request.user = user
    perm = IsStaffOrGroupWrite()
    assert perm.has_permission(request, view=None) is True


@pytest.mark.django_db
def test_is_staff_or_group_write_allows_staff_write():
    factory = APIRequestFactory()
    staff = User.objects.create_user(username="staff", password="pwd", is_staff=True)
    request = factory.post("/", {})
    request.user = staff
    perm = IsStaffOrGroupWrite()
    assert perm.has_permission(request, view=None) is True


@pytest.mark.django_db
def test_is_staff_or_group_write_allows_group_keyword():
    factory = APIRequestFactory()
    group = Group.objects.create(name="Operaciones")
    user = User.objects.create_user(username="bob", password="pwd")
    user.groups.add(group)
    request = factory.post("/", {})
    request.user = user
    perm = IsStaffOrGroupWrite()
    assert perm.has_permission(request, view=None) is True


@pytest.mark.django_db
def test_rol_requerido_superuser_bypass():
    user = User.objects.create_user(username="su", password="pwd", is_superuser=True)
    result = rol_requerido(["admin"])(lambda r: "ok")(type("R", (), {"user": user})())
    assert result == "ok"


@pytest.mark.django_db
def test_rol_requerido_grupo_valido():
    group = Group.objects.create(name="AdminGroup")
    user = User.objects.create_user(username="admin_g", password="pwd")
    user.groups.add(group)
    result = rol_requerido(["AdminGroup"])(lambda r: "ok")(type("R", (), {"user": user})())
    assert result == "ok"


@pytest.mark.django_db
def test_rol_requerido_grupo_invalido_raise():
    group = Group.objects.create(name="Ventas")
    user = User.objects.create_user(username="vendedor_g", password="pwd")
    user.groups.add(group)
    with pytest.raises(PermissionDenied):
        rol_requerido(["AdminGroup"])(lambda r: "ok")(type("R", (), {"user": user})())


@pytest.mark.django_db
def test_rol_requerido_usuario_inactivo_raise():
    user = User.objects.create_user(username="inactivo", password="pwd", is_active=False)
    with pytest.raises(PermissionDenied):
        rol_requerido(["admin"])(lambda r: "ok")(type("R", (), {"user": user})())


@pytest.mark.django_db
def test_is_staff_or_group_write_denies_non_privileged_write():
    factory = APIRequestFactory()
    group = Group.objects.create(name="Finanzas")
    user = User.objects.create_user(username="charlie", password="pwd")
    user.groups.add(group)
    request = factory.post("/", {})
    request.user = user
    perm = IsStaffOrGroupWrite()
    assert perm.has_permission(request, view=None) is False
