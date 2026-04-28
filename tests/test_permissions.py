import pytest
from django.contrib.auth.models import Group, User
from rest_framework.test import APIRequestFactory

from core.permissions import IsStaffOrGroupWrite


@pytest.mark.django_db
def test_is_staff_or_group_write_denies_anonymous():
    factory = APIRequestFactory()
    request = factory.get('/')
    request.user = type('Anon', (), {'is_authenticated': False})()
    perm = IsStaffOrGroupWrite()
    assert perm.has_permission(request, view=None) is False


@pytest.mark.django_db
def test_is_staff_or_group_write_allows_safe_authenticated():
    factory = APIRequestFactory()
    user = User.objects.create_user(username='alice', password='pwd')
    request = factory.get('/')
    request.user = user
    perm = IsStaffOrGroupWrite()
    assert perm.has_permission(request, view=None) is True


@pytest.mark.django_db
def test_is_staff_or_group_write_allows_staff_write():
    factory = APIRequestFactory()
    staff = User.objects.create_user(username='staff', password='pwd', is_staff=True)
    request = factory.post('/', {})
    request.user = staff
    perm = IsStaffOrGroupWrite()
    assert perm.has_permission(request, view=None) is True


@pytest.mark.django_db
def test_is_staff_or_group_write_allows_group_keyword():
    factory = APIRequestFactory()
    group = Group.objects.create(name='Operaciones')
    user = User.objects.create_user(username='bob', password='pwd')
    user.groups.add(group)
    request = factory.post('/', {})
    request.user = user
    perm = IsStaffOrGroupWrite()
    assert perm.has_permission(request, view=None) is True


@pytest.mark.django_db
def test_is_staff_or_group_write_denies_non_privileged_write():
    factory = APIRequestFactory()
    group = Group.objects.create(name='Finanzas')
    user = User.objects.create_user(username='charlie', password='pwd')
    user.groups.add(group)
    request = factory.post('/', {})
    request.user = user
    perm = IsStaffOrGroupWrite()
    assert perm.has_permission(request, view=None) is False
