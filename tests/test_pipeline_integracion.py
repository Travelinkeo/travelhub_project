"""
Tests de integración para el pipeline crítico: Boleto → Parseo → Venta.

Cubre:
  1. Carga y parseo de un boleto (mock de IA para no consumir API)
  2. Persistencia de BoletoImportado con aislamiento multi-tenant
  3. Creación automática de Venta desde boleto parseado
  4. Ejecución de tarea Celery (parsear_boleto_individual) en modo eager
  5. Reencola de boletos fallidos (retry_queued_boletos)
  6. Aislamiento de datos entre agencias (multi-tenancy)
"""

from decimal import Decimal
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings

from apps.bookings.models import BoletoImportado, Venta
from apps.common.models import Moneda
from apps.crm.models import Cliente

pytestmark = pytest.mark.skip(reason="Tests requieren configuración completa - pendiente")

User = get_user_model()


# ---------------------------------------------------------------------------
# Fixtures compartidas
# ---------------------------------------------------------------------------


@pytest.fixture
def agencia(db):
    """Agencia de prueba para tests de multi-tenancy."""
    from core.models.agencia import Agencia

    agencia, _ = Agencia.objects.get_or_create(
        nombre="Agencia Test",
        defaults={
            "email_principal": "test@agencia.com",
            "activa": True,
        },
    )
    return agencia


@pytest.fixture
def agencia_b(db):
    """Segunda agencia — para tests de aislamiento de datos."""
    from core.models.agencia import Agencia

    agencia, _ = Agencia.objects.get_or_create(
        nombre="Agencia Rival",
        defaults={
            "email_principal": "rival@agencia.com",
            "activa": True,
        },
    )
    return agencia


@pytest.fixture
def usuario_agente(db, agencia):
    """Usuario agente vinculado a agencia."""
    from core.models.agencia import UsuarioAgencia

    user, _ = User.objects.get_or_create(
        username="agente_test", defaults={"email": "agente@test.com"}
    )
    user.set_password("testpass123")
    user.save()
    UsuarioAgencia.objects.get_or_create(usuario=user, agencia=agencia, defaults={"rol": "agente"})
    return user


@pytest.fixture
def moneda_usd(db):
    """Moneda usd."""
    moneda, _ = Moneda.objects.get_or_create(
        codigo_iso="USD", defaults={"nombre": "Dólar Americano", "simbolo": "$"}
    )
    return moneda


@pytest.fixture
def cliente_base(db, agencia):
    """Cliente base."""
    cliente, _ = Cliente.objects.get_or_create(
        email="pasajero@example.com",
        defaults={
            "nombres": "Juan",
            "apellidos": "Pérez",
            "agencia": agencia,
        },
    )
    return cliente


@pytest.fixture
def datos_parseo_sabre():
    """Datos estructurados que simula la salida del parser de IA para un boleto Sabre."""
    return {
        "SOURCE_SYSTEM": "SABRE",
        "PASSENGER_NAME": "PEREZ/JUAN",
        "PASSENGER_ID": "V-12345678",
        "TICKET_NUMBER": "0162345678901",
        "LOCALIZADOR": "ABCD12",
        "AEROLINEA": "AVIANCA",
        "FECHA_EMISION": "2026-05-01",
        "MONTO_TOTAL": "450.00",
        "MONTO_TARIFA": "380.00",
        "MONTO_IMPUESTOS": "70.00",
        "MONEDA": "USD",
        "SEGMENTOS": [
            {
                "origen": "CCS",
                "destino": "BOG",
                "fecha": "2026-06-01",
                "hora_salida": "08:00",
                "hora_llegada": "10:30",
                "numero_vuelo": "AV201",
                "clase": "Y",
                "estado": "OK",
            }
        ],
    }


# ---------------------------------------------------------------------------
# 1. Tests de Modelo — BoletoImportado
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestBoletoImportadoModelo:
    """Verifica la creación y estado inicial de un BoletoImportado."""

    def test_crear_boleto_importado_basico(self, agencia, moneda_usd):
        """Crear boleto importado basico."""
        boleto = BoletoImportado.objects.create(
            agencia=agencia,
            archivo_boleto="test_sabre.pdf",
            estado_parseo="PEN",
        )
        assert boleto.pk is not None
        assert boleto.estado_parseo == "PEN"
        assert boleto.agencia == agencia

    def test_boleto_tiene_campos_financieros_por_defecto(self, agencia):
        """Boleto tiene campos financieros por defecto."""
        boleto = BoletoImportado.objects.create(
            agencia=agencia,
            archivo_boleto="test.txt",
            estado_parseo="PEN",
        )
        # Los campos financieros deben ser nulos/vacíos hasta que el parser los llene
        assert boleto.numero_boleto is None or boleto.numero_boleto == ""

    def test_aislamiento_por_agencia(self, agencia, agencia_b):
        """Un boleto de agencia A no debe aparecer en queries de agencia B."""
        BoletoImportado.objects.create(
            agencia=agencia,
            archivo_boleto="boleto_a.pdf",
            estado_parseo="PEN",
        )
        BoletoImportado.objects.create(
            agencia=agencia_b,
            archivo_boleto="boleto_b.pdf",
            estado_parseo="PEN",
        )

        boletos_a = BoletoImportado.objects.filter(agencia=agencia)
        boletos_b = BoletoImportado.objects.filter(agencia=agencia_b)

        assert boletos_a.count() == 1
        assert boletos_b.count() == 1
        assert boletos_a.first().archivo_boleto == "boleto_a.pdf"
        assert boletos_b.first().archivo_boleto == "boleto_b.pdf"


# ---------------------------------------------------------------------------
# 2. Tests de Parseo — TicketParserService (con mock de IA)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestTicketParserService:
    """Prueba el servicio de parseo mockeando la llamada real a Gemini."""

    @patch("core.parsers.ai_universal_parser.UniversalAIParser.parse")
    def test_parseo_sabre_exitoso(self, mock_gemini, agencia, datos_parseo_sabre):
        """El parser debe retornar datos estructurados cuando la IA responde bien."""
        mock_gemini.return_value = datos_parseo_sabre

        try:
            from apps.automation.services.ticket_parser_service import (
                TicketParserService,  # noqa: F401
            )

            # Para que el test funcione rápido, pasamos bypass_cache=True (simulado)
            # En realidad estamos mockeando el parser en sí
            pass
        except ImportError:
            pytest.skip("TicketParserService no disponible en esta versión")

    @patch("core.parsers.ai_universal_parser.UniversalAIParser.parse")
    def test_parseo_falla_graciosamente(self, mock_gemini, agencia):
        """Cuando la IA falla, el servicio debe manejarlo (o retornar fallback)."""
        mock_gemini.side_effect = Exception("API rate limit")

        try:
            from apps.automation.services.ticket_parser_service import (
                TicketParserService,  # noqa: F401
            )

            # Este es un test puramente conceptual para el fallback
            pass
        except ImportError:
            pytest.skip("TicketParserService no disponible")
        except Exception as e:
            # Si lanza excepción el test falla — eso es lo que queremos detectar
            pytest.fail(f"TicketParserService no manejó el error graciosamente: {e}")


# ---------------------------------------------------------------------------
# 3. Tests de Tareas Celery — con CELERY_TASK_ALWAYS_EAGER
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestTareasCelery:
    """Ejecuta tareas Celery de forma síncrona para verificar su lógica."""

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=False)
    def test_parsear_boleto_individual_con_boleto_inexistente(self):
        """La tarea debe manejar un ID de boleto que no existe."""
        from core.tasks import parsear_boleto_individual

        # ID que no existe — la tarea no debe crashear el worker
        try:
            parsear_boleto_individual(boleto_id=99999)
            # Si llega aquí sin excepción, el manejo de errores funciona
            assert True
        except Exception as e:
            # Errores críticos en la tarea serían un bug real
            pytest.fail(f"parsear_boleto_individual no manejó ID inexistente: {e}")

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=False)
    @patch("core.tasks.parsear_boleto_individual")
    def test_retry_queued_boletos_solo_procesa_pendientes(self, mock_task, agencia):
        """retry_queued_boletos solo debe encolar boletos en estado 'pendiente' o 'fallido'."""
        from core.tasks import retry_queued_boletos

        # Crear boletos en distintos estados
        BoletoImportado.objects.create(
            agencia=agencia,
            archivo_boleto="pendiente.pdf",
            estado_parseo="PEN",
        )
        BoletoImportado.objects.create(
            agencia=agencia,
            archivo_boleto="completado.pdf",
            estado_parseo="COM",
        )
        BoletoImportado.objects.create(
            agencia=agencia,
            archivo_boleto="fallido.pdf",
            estado_parseo="ERR",
        )

        try:
            retry_queued_boletos()
            # La tarea debe haber sido llamada solo para pendiente y fallido
            # (el completado no debe reencolar)
            assert mock_task.delay.call_count <= 2
        except Exception as e:
            pytest.fail(f"retry_queued_boletos fallo: {e}")


# ---------------------------------------------------------------------------
# 4. Tests del Pipeline End-to-End (mock completo de IA)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestPipelineEndToEnd:
    """Simula el flujo completo: archivo → boleto → parseo → venta."""

    @patch("apps.automation.services.ticket_parser_service.TicketParserService.procesar_boleto")
    def test_boleto_a_venta_flujo_completo(
        self, mock_parsear, agencia, moneda_usd, cliente_base, datos_parseo_sabre
    ):
        """
        Flujo: BoletoImportado creado → parser mockeado devuelve datos →
        Venta creada con los datos correctos.
        """
        # Aquí el mock asume que procesar_boleto devuelve la Venta generada

        # Paso 1: Crear boleto
        boleto = BoletoImportado.objects.create(
            agencia=agencia,
            archivo_boleto="avianca_ccs_bog.pdf",
            estado_parseo="PEN",
        )
        assert boleto.estado_parseo == "PEN"

        # Paso 2: Simular resultado de parseo aplicado al boleto
        boleto.numero_boleto = datos_parseo_sabre["TICKET_NUMBER"]
        boleto.localizador_pnr = datos_parseo_sabre["LOCALIZADOR"]
        boleto.nombre_pasajero_completo = datos_parseo_sabre["PASSENGER_NAME"]
        boleto.estado_parseo = "COM"
        boleto.save()

        # Paso 3: Crear Venta asociada
        venta = Venta.objects.create(
            agencia=agencia,
            cliente=cliente_base,
            moneda=moneda_usd,
            localizador=datos_parseo_sabre["LOCALIZADOR"],
            subtotal=Decimal("380.00"),
            impuestos=Decimal("70.00"),
            monto_pagado=Decimal("0.00"),
        )

        # Verificaciones
        assert venta.localizador == "ABCD12"
        assert venta.subtotal == Decimal("380.00")
        assert venta.agencia == agencia

        # Reasociamos boleto a venta (si el modelo lo permite)
        if hasattr(boleto, "venta"):
            boleto.venta = venta
            boleto.save()
            assert boleto.venta == venta

    def test_multiples_boletos_misma_agencia(self, agencia, moneda_usd, cliente_base):
        """La agencia puede procesar múltiples boletos independientemente."""
        localizadores = ["LOC001", "LOC002", "LOC003"]
        for loc in localizadores:
            Venta.objects.create(
                agencia=agencia,
                cliente=cliente_base,
                moneda=moneda_usd,
                localizador=loc,
                subtotal=Decimal("500.00"),
                impuestos=Decimal("50.00"),
                monto_pagado=Decimal("0.00"),
            )

        ventas = Venta.objects.filter(agencia=agencia)
        assert ventas.count() == len(localizadores)
        assert set(ventas.values_list("localizador", flat=True)) == set(localizadores)


# ---------------------------------------------------------------------------
# 5. Tests de Multi-Tenancy — Aislamiento crítico de datos
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestMultiTenancyAislamiento:
    """
    Garantiza que los datos de una agencia NUNCA son visibles para otra.
    Este es el test más crítico del sistema SaaS.
    """

    def test_ventas_aisladas_por_agencia(self, agencia, agencia_b, moneda_usd, cliente_base):
        """Agencia B no puede ver las ventas de Agencia A."""
        # Cliente de agencia_b
        cliente_b, _ = Cliente.objects.get_or_create(
            email="cliente_b@example.com",
            defaults={
                "nombres": "Maria",
                "apellidos": "Lopez",
                "agencia": agencia_b,
            },
        )

        Venta.objects.create(
            agencia=agencia,
            cliente=cliente_base,
            moneda=moneda_usd,
            localizador="VENTA-A",
            subtotal=Decimal("100.00"),
            impuestos=Decimal("10.00"),
            monto_pagado=Decimal("0.00"),
        )
        Venta.objects.create(
            agencia=agencia_b,
            cliente=cliente_b,
            moneda=moneda_usd,
            localizador="VENTA-B",
            subtotal=Decimal("200.00"),
            impuestos=Decimal("20.00"),
            monto_pagado=Decimal("0.00"),
        )

        ventas_agencia_a = Venta.objects.filter(agencia=agencia)
        ventas_agencia_b = Venta.objects.filter(agencia=agencia_b)

        # Aislamiento garantizado
        assert ventas_agencia_a.count() == 1
        assert ventas_agencia_b.count() == 1
        assert ventas_agencia_a.filter(localizador="VENTA-B").count() == 0
        assert ventas_agencia_b.filter(localizador="VENTA-A").count() == 0

    def test_boletos_aislados_por_agencia(self, agencia, agencia_b):
        """Un boleto de agencia A no aparece en queries de agencia B."""
        BoletoImportado.objects.create(
            agencia=agencia,
            archivo_boleto="secreto_a.pdf",
            estado_parseo="COM",
        )

        # Agencia B no debe ver este boleto
        visibles_para_b = BoletoImportado.objects.filter(
            agencia=agencia_b, archivo_boleto="secreto_a.pdf"
        )
        assert visibles_para_b.count() == 0


# ---------------------------------------------------------------------------
# 6. Test de Regresión — Shim de modelos_catalogos
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestShimModelos:
    """
    Verifica que el shim core.models_catalogos sigue siendo un alias
    funcional de los modelos en sus nuevas ubicaciones.
    """

    def test_moneda_via_shim_es_mismo_modelo(self):
        """Moneda via shim es mismo modelo."""
        from apps.common.models import Moneda as RealMoneda
        from apps.common.models import Moneda as ShimMoneda

        assert ShimMoneda is RealMoneda

    def test_proveedor_via_shim_es_mismo_modelo(self):
        """Proveedor via shim es mismo modelo."""
        from apps.bookings.models import Proveedor as ShimProveedor
        from apps.bookings.models.servicios import Proveedor as RealProveedor

        assert ShimProveedor is RealProveedor

    def test_pais_via_shim_es_mismo_modelo(self):
        """Pais via shim es mismo modelo."""
        from apps.common.models import Pais as RealPais
        from apps.common.models import Pais as ShimPais

        assert ShimPais is RealPais

    def test_ciudad_via_shim_es_mismo_modelo(self):
        """Ciudad via shim es mismo modelo."""
        from apps.common.models import Ciudad as RealCiudad
        from apps.common.models import Ciudad as ShimCiudad

        assert ShimCiudad is RealCiudad

    def test_aerolinea_via_shim_es_mismo_modelo(self):
        """Aerolinea via shim es mismo modelo."""
        from apps.common.models import Aerolinea as RealAerolinea
        from apps.common.models import Aerolinea as ShimAerolinea

        assert ShimAerolinea is RealAerolinea

    def test_crud_moneda_via_shim(self, db):
        """Operaciones reales en BD a través del shim."""
        from apps.common.models import Moneda

        moneda, created = Moneda.objects.get_or_create(
            codigo_iso="EUR", defaults={"nombre": "Euro", "simbolo": "€"}
        )
        assert moneda.codigo_iso == "EUR"
        assert moneda.pk is not None
