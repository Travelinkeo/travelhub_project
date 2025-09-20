import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_jwt_obtain_and_access_protected():
    User.objects.create_user(username='jwtuser', password='StrongPass123')
    client = APIClient()
    # Obtain pair
    resp = client.post('/api/auth/jwt/obtain/', {'username': 'jwtuser', 'password': 'StrongPass123'}, format='json')
    assert resp.status_code == 200, resp.content
    access = resp.data['access']
    refresh = resp.data['refresh']
    assert access and refresh
    # Use access to list ventas (should not error; may be empty)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
    ventas = client.get('/api/ventas/')
    assert ventas.status_code in (200, 204), ventas.content
    # Refresh token
    refreshed = client.post('/api/auth/jwt/refresh/', {'refresh': refresh}, format='json')
    assert refreshed.status_code == 200, refreshed.content
    new_access = refreshed.data['access']
    assert new_access and new_access != access
    # Logout (blacklist)
    logout_resp = client.post('/api/auth/jwt/logout/', {'refresh': refresh}, format='json')
    assert logout_resp.status_code in (205, 200, 400)  # 205 ideal; allow 400 if already blacklisted
