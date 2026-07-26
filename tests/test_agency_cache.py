"""Tests para el servicio de caching de agencias"""

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache

from core.models import Agencia, UsuarioAgencia

User = get_user_model()


@pytest.mark.django_db
class TestAgencyCacheService:
    """Tests para el servicio de caching de agencias"""

    @pytest.fixture(autouse=True)
    def setup_data(self):
        """Configuración común para todos los tests"""
        cache.clear()
        self.agencia = Agencia.objects.create(nombre="Test Agency")
        self.user = User.objects.create_user(
            username="testuser", email="test@agency.com", password="testpass123"
        )
        self.usuario_agencia = UsuarioAgencia.objects.create(
            usuario=self.user, agencia=self.agencia, activo=True, rol="admin"
        )

    def test_get_agencia_from_cache_miss(self):
        """Test cache miss - debe consultar BD"""
        from core.services.agency_cache_service import get_agencia_from_cache

        # Primer acceso - cache miss
        result = get_agencia_from_cache(self.agencia.pk)

        assert result is not None
        assert result["id"] == self.agencia.pk
        assert result["nombre"] == "Test Agency"

    def test_get_agencia_from_cache_hit(self):
        """Test cache hit - debe retornar desde cache"""
        from core.services.agency_cache_service import get_agencia_from_cache

        # Primer acceso - populate cache
        result1 = get_agencia_from_cache(self.agencia.pk)
        assert result1 is not None

        # Segundo acceso - cache hit
        result2 = get_agencia_from_cache(self.agencia.pk)
        assert result2 == result1

    def test_invalidate_agencia_cache(self):
        """Test invalidación de cache de agencia"""
        from core.services.agency_cache_service import (
            get_agencia_from_cache,
            invalidate_agencia_cache,
        )

        # Populate cache
        result1 = get_agencia_from_cache(self.agencia.pk)
        assert result1 is not None

        # Invalidar
        invalidate_agencia_cache(self.agencia.pk)

        # Verificar que se puede obtener de nuevo (nuevo cache miss)
        result2 = get_agencia_from_cache(self.agencia.pk)
        assert result2 is not None

    def test_get_usuario_agencias_from_cache(self):
        """Test cache de agencias de usuario"""
        from core.services.agency_cache_service import get_usuario_agencias_from_cache

        result = get_usuario_agencias_from_cache(self.user.pk)

        assert isinstance(result, list)
        assert self.agencia.pk in result

    def test_invalidate_usuario_agencias_cache(self):
        """Test invalidación de cache de usuario-agencias"""
        from core.services.agency_cache_service import (
            get_usuario_agencias_from_cache,
            invalidate_usuario_agencias_cache,
        )

        # Populate cache
        result1 = get_usuario_agencias_from_cache(self.user.pk)
        assert len(result1) == 1

        # Invalidar
        invalidate_usuario_agencias_cache(self.user.pk)

        # Verificar que se puede obtener de nuevo
        result2 = get_usuario_agencias_from_cache(self.user.pk)
        assert isinstance(result2, list)

    def test_cache_agencia_dashboard_data(self):
        """Test cache de datos de dashboard"""
        from core.services.agency_cache_service import (
            cache_agencia_dashboard_data,
            get_agencia_dashboard_data,
        )

        test_data = {"ventas": 100, "ingresos": 5000}

        # Cache data
        assert cache_agencia_dashboard_data(self.agencia.pk, test_data) is True

        # Retrieve data
        cached = get_agencia_dashboard_data(self.agencia.pk)
        assert cached == test_data

    def test_cache_query_result(self):
        """Test cache genérico de queries"""
        from core.services.agency_cache_service import cache_query_result, get_cached_query_result

        test_key = "test_query_key"
        test_data = [1, 2, 3]

        # Cache data
        assert cache_query_result(test_key, test_data) is True

        # Retrieve data
        cached = get_cached_query_result(test_key)
        assert cached == test_data

    def test_cache_query_result_miss(self):
        """Test cache miss genérico"""
        from core.services.agency_cache_service import get_cached_query_result

        result = get_cached_query_result("nonexistent_key")
        assert result is None


@pytest.mark.django_db
class TestSecurityCacheIntegration:
    """Tests para la integración de cache en security.py"""

    @pytest.fixture(autouse=True)
    def setup_data(self):
        """setup_data."""
        cache.clear()
        self.agencia = Agencia.objects.create(nombre="Test Agency")
        self.user = User.objects.create_user(
            username="testuser", email="test@agency.com", password="testpass123"
        )
        self.usuario_agencia = UsuarioAgencia.objects.create(
            usuario=self.user, agencia=self.agencia, activo=True, rol="admin"
        )

    def test_get_user_active_agency_cached(self):
        """Test que get_user_active_agency usa cache"""
        from core.security import get_user_active_agency

        # Primer acceso - cache miss
        result1 = get_user_active_agency(self.user)
        assert result1 is not None
        assert result1.pk == self.agencia.pk

        # Segundo acceso - cache hit
        result2 = get_user_active_agency(self.user)
        assert result2 is not None
        assert result2.pk == self.agencia.pk

    def test_get_user_active_agency_no_agencia(self):
        """Test usuario sin agencia"""
        from core.security import get_user_active_agency

        user2 = User.objects.create_user(
            username="testuser2", email="test2@agency.com", password="testpass123"
        )

        result = get_user_active_agency(user2)
        assert result is None

    def test_invalidate_user_agencia_cache(self):
        """Test invalidación de cache de usuario"""
        from core.security import get_user_active_agency, invalidate_user_agencia_cache

        # Populate cache
        result1 = get_user_active_agency(self.user)
        assert result1 is not None

        # Invalidar
        invalidate_user_agencia_cache(self.user.pk)

        # Verificar que se puede obtener de nuevo
        result2 = get_user_active_agency(self.user)
        assert result2 is not None
