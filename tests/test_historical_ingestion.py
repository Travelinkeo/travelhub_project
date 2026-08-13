from django.test import TestCase

from apps.automation.services.rag_historical_ingestion import RAGHistoricalEmailIngestionService
from apps.cms.models import KBHistoricalEmailLog
from core.models import Agencia


class RAGHistoricalIngestionTestCase(TestCase):
    """Pruebas unitarias para la ingesta histórica de correos RAG."""

    def setUp(self):
        self.agencia, _ = Agencia.objects.get_or_create(nombre="Travelinkeo Hist Test")

    def test_is_informative_email_filtering(self):
        # Correo de ruido transaccional
        is_info_noise = RAGHistoricalEmailIngestionService.is_informative_email(
            subject="Su código de verificación OTP es 489201",
            body="Estimado cliente, use este código para restablecer su contraseña.",
            sender="security@google.com",
        )
        self.assertFalse(is_info_noise)

        # Correo informativo de aerolínea
        is_info_useful = RAGHistoricalEmailIngestionService.is_informative_email(
            subject="Comunicado Oficial: Nueva política de equipaje Avianca 2024",
            body="Informamos a todas las agencias sobre los acuerdos tarifarios y la comisión del 6% en rutas internacionales.",
            sender="boletines@avianca.com",
        )
        self.assertTrue(is_info_useful)

    def test_log_creation_and_idempotency(self):
        log = KBHistoricalEmailLog.objects.create(
            agencia=self.agencia,
            message_id="travelinkeo@gmail.com_1001",
            source_email="travelinkeo@gmail.com",
            subject="Acuerdo Comercial Copa Airlines",
            sender="ventas@copaair.com",
            status="PROCESSED",
            chunks_created=2,
        )
        self.assertEqual(log.status, "PROCESSED")
        self.assertTrue(
            KBHistoricalEmailLog.objects.filter(
                message_id="travelinkeo@gmail.com_1001", agencia=self.agencia
            ).exists()
        )
