"""
tests/test_suscripcion_billing.py
===================================
Suite de Pruebas Unitarias e Integración para Registro Self-Service de Agencias,
Gestión de Suscripciones SaaS y Control de Cuotas.
"""

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from core.models.agencia import Agencia
from core.services.suscripcion_service import SuscripcionService


@pytest.mark.django_db
class TestSuscripcionService:
    """Tests unitarios para el servicio SuscripcionService."""

    def test_register_new_tenant_success(self):
        """Verifica que el registro de una nueva agencia sea atómico y configure los objetos correspondientes."""
        agencia, user = SuscripcionService.register_new_tenant(
            nombre_agencia="Viajes Turis",
            email_propietario="contacto@viajesturis.com",
            password="SecurePassword123!",
            first_name="Carlos",
            last_name="Perez",
            plan="FREE",
            telefono="+584141234567",
        )

        assert agencia.id is not None
        assert agencia.nombre == "Viajes Turis"
        assert agencia.propietario == user
        assert agencia.activa is True
        assert agencia.configuracion is not None
        assert agencia.configuracion.plan == "FREE"
        assert agencia.configuracion.limite_ventas_mes == 30
        assert agencia.configuracion.ventas_mes_actual == 0

    def test_check_tenant_quota_allowed_and_exceeded(self):
        """Verifica que la comprobación de cuota permita o bloquee según consumos."""
        agencia, _ = SuscripcionService.register_new_tenant(
            nombre_agencia="Agencia Cuotas",
            email_propietario="admin@agenciacuotas.com",
            password="SecurePassword123!",
            plan="FREE",
        )

        # 1. Cuota inicial dentro del límite
        allowed, current, limit, msg = SuscripcionService.check_tenant_quota(
            agencia, feature="boletos"
        )
        assert allowed is True
        assert current == 0
        assert limit == 30

        # 2. Simular consumo máximo alcanzado
        agencia.configuracion.ventas_mes_actual = 30
        agencia.configuracion.save()

        allowed, current, limit, msg = SuscripcionService.check_tenant_quota(
            agencia, feature="boletos"
        )
        assert allowed is False
        assert current == 30
        assert limit == 30
        assert "Ha alcanzado el límite mensual" in msg

    def test_upgrade_plan_increases_limits(self):
        """Verifica que hacer upgrade de plan incremente los límites inmediatamente."""
        agencia, _ = SuscripcionService.register_new_tenant(
            nombre_agencia="Agencia Upgrade",
            email_propietario="admin@upgrade.com",
            password="SecurePassword123!",
            plan="FREE",
        )

        config_upgraded = SuscripcionService.upgrade_plan(agencia=agencia, new_plan="PRO")

        assert config_upgraded.plan == "PRO"
        assert config_upgraded.limite_ventas_mes == 1000
        assert config_upgraded.limite_usuarios == 15

        # La cuota previamente bloqueada ahora debe estar permitida
        agencia.configuracion.ventas_mes_actual = 50
        agencia.configuracion.save()

        allowed, current, limit, _ = SuscripcionService.check_tenant_quota(
            agencia, feature="boletos"
        )
        assert allowed is True
        assert limit == 1000


@pytest.mark.django_db
class TestBillingAPIs:
    """Tests de integración para los endpoints REST de Onboarding y Billing."""

    def setup_method(self):
        self.client = APIClient()

    def test_api_register_tenant_public(self):
        """Prueba la API pública de autoregistro POST /api/auth/register-tenant/"""
        payload = {
            "nombre_agencia": "Agencia API SelfService",
            "email_propietario": "ceo@apiselfservice.com",
            "password": "PasswordExito123!",
            "plan": "BASIC",
            "first_name": "Laura",
            "last_name": "Gomez",
            "telefono": "+584129876543",
        }

        response = self.client.post("/api/auth/register-tenant/", payload, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["agencia_nombre"] == "Agencia API SelfService"
        assert response.data["plan"] == "BASIC"

        agencia = Agencia.objects.get(id=response.data["agencia_id"])
        assert agencia.configuracion.plan == "BASIC"
        assert agencia.configuracion.limite_ventas_mes == 200

    def test_api_current_plan_and_checkout(self):
        """Prueba consultar el plan actual e iniciar un checkout de suscripción."""
        agencia, user = SuscripcionService.register_new_tenant(
            nombre_agencia="Agencia Endpoint",
            email_propietario="admin@endpoint.com",
            password="SecurePassword123!",
            plan="FREE",
        )

        self.client.force_authenticate(user=user)

        # 1. Consultar plan actual
        res_current = self.client.get("/api/billing/current-plan/")
        assert res_current.status_code == status.HTTP_200_OK
        assert res_current.data["plan"] == "FREE"
        assert res_current.data["limite_ventas_mes"] == 30

        # 2. Upgrade vía Checkout API
        checkout_payload = {
            "new_plan": "PRO",
            "metodo_pago": "pagomovil",
            "referencia_pago": "PM-99887766",
        }
        res_checkout = self.client.post("/api/billing/checkout/", checkout_payload, format="json")

        assert res_checkout.status_code == status.HTTP_200_OK
        assert res_checkout.data["plan"] == "PRO"
        assert res_checkout.data["limite_ventas_mes"] == 1000
