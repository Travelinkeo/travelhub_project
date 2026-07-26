import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.crm.models import (
    Cliente,
    ComisionFreelancer,
    FreelancerProfile,
    OportunidadViaje,
    Pasajero,
)


@pytest.mark.django_db
class TestClienteModel:
    """TestClienteModel."""

    def test_crear_cliente(self, agencia_premium):
        """test_crear_cliente."""
        cliente = Cliente.objects.create(
            agencia=agencia_premium, nombres="Juan", apellidos="Pérez", email="juan@example.com"
        )
        assert cliente.pk is not None
        assert cliente.id_cliente == cliente.id
        assert str(cliente) == "Juan Pérez"

    def test_cliente_str_sin_apellidos(self, agencia_premium):
        """test_cliente_str_sin_apellidos."""
        cliente = Cliente.objects.create(agencia=agencia_premium, nombres="María")
        assert str(cliente).strip() == "María"

    def test_cliente_es_frecuente_por_puntos(self, agencia_premium):
        """test_cliente_es_frecuente_por_puntos."""
        cliente = Cliente.objects.create(
            agencia=agencia_premium,
            nombres="Carlos",
            puntos_fidelidad=1500,
        )
        assert cliente.calcular_cliente_frecuente() is True
        assert cliente.es_cliente_frecuente is True

    def test_cliente_no_frecuente_sin_puntos(self, agencia_premium):
        """test_cliente_no_frecuente_sin_puntos."""
        cliente = Cliente.objects.create(
            agencia=agencia_premium,
            nombres="Ana",
            puntos_fidelidad=100,
        )
        assert cliente.calcular_cliente_frecuente() is False
        assert cliente.es_cliente_frecuente is False

    def test_cliente_tipo_default(self, agencia_premium):
        """test_cliente_tipo_default."""
        cliente = Cliente.objects.create(agencia=agencia_premium, nombres="Test")
        assert cliente.tipo_cliente == Cliente.TipoCliente.PARTICULAR

    def test_cliente_tipo_cliente_choices(self, agencia_premium):
        """test_cliente_tipo_cliente_choices."""
        cliente = Cliente.objects.create(
            agencia=agencia_premium,
            nombres="Empresa",
            tipo_cliente=Cliente.TipoCliente.CORPORATIVO,
        )
        assert cliente.tipo_cliente == "COR"

    def test_cliente_soft_delete_isolation(self, agencia_premium):
        """test_cliente_soft_delete_isolation."""
        cliente = Cliente.objects.create(agencia=agencia_premium, nombres="Test")
        cliente.delete()
        assert Cliente.objects.filter(pk=cliente.pk).count() == 0
        assert Cliente.all_objects.filter(pk=cliente.pk).count() == 1

    def test_cliente_multi_tenant_isolation(self, agencia_premium, agencia_estandar):
        """test_cliente_multi_tenant_isolation."""
        Cliente.objects.create(agencia=agencia_premium, nombres="Agency1")
        Cliente.objects.create(agencia=agencia_estandar, nombres="Agency2")
        assert Cliente.objects.filter(agencia=agencia_premium).count() == 1
        assert Cliente.objects.filter(agencia=agencia_estandar).count() == 1

    def test_cliente_uuid_auto_generado(self, agencia_premium):
        """test_cliente_uuid_auto_generado."""
        cliente = Cliente.objects.create(agencia=agencia_premium, nombres="Test")
        assert cliente.uuid is not None


@pytest.mark.django_db
class TestPasajeroModel:
    """TestPasajeroModel."""

    def test_crear_pasajero(self, agencia_premium):
        """test_crear_pasajero."""
        pasajero = Pasajero.objects.create(
            agencia=agencia_premium,
            nombres="Ana",
            apellidos="García",
            email="ana@example.com",
        )
        assert pasajero.pk is not None

    def test_pasajero_asociado_a_cliente(self, agencia_premium):
        """test_pasajero_asociado_a_cliente."""
        cliente = Cliente.objects.create(agencia=agencia_premium, nombres="Test")
        pasajero = Pasajero.objects.create(
            agencia=agencia_premium, nombres="Pasajero", apellidos="Test"
        )
        cliente.pasajeros.add(pasajero)
        assert pasajero in cliente.pasajeros.all()

    def test_pasajero_soft_delete(self, agencia_premium):
        """test_pasajero_soft_delete."""
        pasajero = Pasajero.objects.create(agencia=agencia_premium, nombres="Test")
        pasajero.delete()
        assert Pasajero.objects.filter(pk=pasajero.pk).count() == 0
        assert Pasajero.all_objects.filter(pk=pasajero.pk).count() == 1


@pytest.mark.django_db
class TestOportunidadViaje:
    """TestOportunidadViaje."""

    def test_crear_oportunidad(self, agencia_premium):
        """test_crear_oportunidad."""
        cliente = Cliente.objects.create(agencia=agencia_premium, nombres="Test")
        op = OportunidadViaje.objects.create(
            agencia=agencia_premium,
            cliente=cliente,
            origen="CCS",
            destino="MAD",
        )
        assert op.pk is not None
        assert op.etapa == OportunidadViaje.Etapa.NUEVO

    def test_oportunidad_defaults(self, agencia_premium):
        """test_oportunidad_defaults."""
        cliente = Cliente.objects.create(agencia=agencia_premium, nombres="Test")
        op = OportunidadViaje.objects.create(
            agencia=agencia_premium, cliente=cliente, origen="CCS", destino="MAD"
        )
        assert op.etapa == OportunidadViaje.Etapa.NUEVO


@pytest.mark.django_db
class TestFreelancerProfile:
    """TestFreelancerProfile."""

    def test_crear_freelancer(self, agencia_premium, usuario_staff):
        """test_crear_freelancer."""
        perfil = FreelancerProfile.objects.create(
            agencia=agencia_premium,
            usuario=usuario_staff,
            comision_fija_por_boleto=5.00,
            porcentaje_comision=10.00,
        )
        assert perfil.pk is not None
        assert perfil.saldo_por_cobrar == 0
        assert perfil.total_historico_pagado == 0

    def test_freelancer_soft_delete(self, agencia_premium, usuario_staff):
        """test_freelancer_soft_delete."""
        perfil = FreelancerProfile.objects.create(agencia=agencia_premium, usuario=usuario_staff)
        perfil.delete()
        assert FreelancerProfile.objects.filter(pk=perfil.pk).count() == 0


@pytest.mark.django_db
class TestComisionFreelancer:
    """TestComisionFreelancer."""

    def test_crear_comision(self, agencia_premium, usuario_staff):
        """test_crear_comision."""
        perfil = FreelancerProfile.objects.create(agencia=agencia_premium, usuario=usuario_staff)
        comision = ComisionFreelancer.objects.create(
            agencia=agencia_premium,
            freelancer=perfil,
            monto_base_venta=1000.00,
            monto_comision_ganada=100.00,
        )
        assert comision.pk is not None
        assert comision.liquidada is False


@pytest.mark.django_db
class TestClienteAPI:
    """TestClienteAPI."""

    def _setup_user_agencia(self, usuario_staff, agencia):
        """_setup_user_agencia."""
        from core.api import UsuarioAgencia

        UsuarioAgencia.objects.get_or_create(
            usuario=usuario_staff, agencia=agencia, defaults={"rol": "admin"}
        )

    def test_list_clientes_authenticated(self, agencia_premium, usuario_staff):
        """test_list_clientes_authenticated."""
        self._setup_user_agencia(usuario_staff, agencia_premium)
        Cliente.objects.create(agencia=agencia_premium, nombres="Juan", apellidos="Pérez")
        client = APIClient()
        client.force_authenticate(user=usuario_staff)
        response = client.get("/crm/api/clientes/")
        assert response.status_code == status.HTTP_200_OK

    def test_list_clientes_unauthenticated(self):
        """test_list_clientes_unauthenticated."""
        client = APIClient()
        response = client.get("/crm/api/clientes/")
        assert response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

    def test_create_cliente_authenticated(self, agencia_premium, usuario_staff):
        """test_create_cliente_authenticated."""
        self._setup_user_agencia(usuario_staff, agencia_premium)
        client = APIClient()
        client.force_authenticate(user=usuario_staff)
        response = client.post(
            "/crm/api/clientes/",
            {"nombres": "María", "apellidos": "Gómez", "email": "maria@example.com"},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["nombres"] == "María"

    def test_retrieve_cliente(self, agencia_premium, usuario_staff):
        """test_retrieve_cliente."""
        self._setup_user_agencia(usuario_staff, agencia_premium)
        cliente = Cliente.objects.create(agencia=agencia_premium, nombres="Juan", apellidos="Pérez")
        client = APIClient()
        client.force_authenticate(user=usuario_staff)
        response = client.get(f"/crm/api/clientes/{cliente.id}/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["nombres"] == "Juan"

    def test_update_cliente(self, agencia_premium, usuario_staff):
        """test_update_cliente."""
        self._setup_user_agencia(usuario_staff, agencia_premium)
        cliente = Cliente.objects.create(agencia=agencia_premium, nombres="Juan", apellidos="Pérez")
        client = APIClient()
        client.force_authenticate(user=usuario_staff)
        response = client.patch(
            f"/crm/api/clientes/{cliente.id}/",
            {"nombres": "Juan Actualizado"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["nombres"] == "Juan Actualizado"

    def test_delete_cliente(self, agencia_premium, usuario_staff):
        """test_delete_cliente."""
        self._setup_user_agencia(usuario_staff, agencia_premium)
        cliente = Cliente.objects.create(agencia=agencia_premium, nombres="Juan", apellidos="Pérez")
        client = APIClient()
        client.force_authenticate(user=usuario_staff)
        response = client.delete(f"/crm/api/clientes/{cliente.id}/")
        assert response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.django_db
class TestPasajeroAPI:
    """TestPasajeroAPI."""

    def _setup_user_agencia(self, usuario_staff, agencia):
        """_setup_user_agencia."""
        from core.api import UsuarioAgencia

        UsuarioAgencia.objects.get_or_create(
            usuario=usuario_staff, agencia=agencia, defaults={"rol": "admin"}
        )

    def test_list_pasajeros_authenticated(self, agencia_premium, usuario_staff):
        """test_list_pasajeros_authenticated."""
        self._setup_user_agencia(usuario_staff, agencia_premium)
        Pasajero.objects.create(agencia=agencia_premium, nombres="Ana", apellidos="García")
        client = APIClient()
        client.force_authenticate(user=usuario_staff)
        response = client.get("/crm/api/pasajeros/")
        assert response.status_code == status.HTTP_200_OK

    def test_create_pasajero_authenticated(self, agencia_premium, usuario_staff):
        """test_create_pasajero_authenticated."""
        self._setup_user_agencia(usuario_staff, agencia_premium)
        client = APIClient()
        client.force_authenticate(user=usuario_staff)
        response = client.post(
            "/crm/api/pasajeros/",
            {"nombres": "Carlos", "apellidos": "López", "email": "carlos@example.com"},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED

    def test_create_pasajero_unauthenticated(self):
        """test_create_pasajero_unauthenticated."""
        client = APIClient()
        response = client.post(
            "/crm/api/pasajeros/",
            {"nombres": "Test", "apellidos": "User"},
            format="json",
        )
        assert response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
