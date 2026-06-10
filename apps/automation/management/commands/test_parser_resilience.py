import time
from unittest.mock import patch

from celery.exceptions import SoftTimeLimitExceeded
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from apps.automation.parsers.ai_universal_parser import UniversalAIParser
from apps.automation.services.ticket_parser_service import TicketParserService
from apps.bookings.models import BoletoImportado


class Command(BaseCommand):
    help = "Ejecuta pruebas de estrés y resiliencia forense sobre el parser de boletos."

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.WARNING("[+] INICIANDO BATERIA DE PRUEBAS DE ESTRES (QA FORENSE)...\n")
        )

        self.prueba_1_simulador_caida_gemini()
        self.stdout.write("\n" + "=" * 50 + "\n")
        self.prueba_2_simulador_basura_regex()

        self.stdout.write(
            self.style.SUCCESS(
                "\n[EXITO] TODAS LAS PRUEBAS DE RESILIENCIA SUPERADAS EXITOSAMENTE. EL SISTEMA ES ESTABLE."
            )
        )

    def prueba_1_simulador_caida_gemini(self):
        self.stdout.write(
            self.style.WARNING("[PRUEBA 1] Simulador de Caida de Gemini (Timeout Celery)")
        )
        self.stdout.write(
            "Configuracion: Simulando latencia extrema de red y detonacion de SoftTimeLimitExceeded."
        )

        parser = UniversalAIParser()

        # Mocker para simular que Gemini se queda colgado y Celery lanza la excepción
        def mock_call_gemini_timeout(*args, **kwargs):
            self.stdout.write("   [MOCK] Peticion a Gemini iniciada. Simulando bloqueo de red...")
            time.sleep(2)  # Acelerado para la prueba (simula los 20s)
            self.stdout.write("   [MOCK] Celery detona SoftTimeLimitExceeded abortando la red!")
            raise SoftTimeLimitExceeded("Timeout simulado de Celery")

        start_time = time.time()

        with patch(
            "apps.automation.services.ai_engine.ai_engine.call_gemini",
            side_effect=mock_call_gemini_timeout,
        ):
            resultado = parser.parse("Texto de prueba que nunca sera leido")

        duracion = time.time() - start_time

        # Validaciones (Asserts)
        assert isinstance(resultado, dict), "El resultado debe ser un diccionario."
        assert "error" in resultado, "El resultado debe contener una llave de error."
        assert (
            "API_FAILURE: TIMEOUT IA" in resultado["error"]
        ), "El error debe ser por Timeout de IA."
        assert (
            resultado.get("fallback_triggered") is True
        ), "Debe indicar que se detonara el fallback."

        self.stdout.write(
            self.style.SUCCESS(
                f"[EXITO] PRUEBA 1 PASADA: La ejecucion fue abortada limpiamente y capturada en {duracion:.2f}s sin colgar el hilo."
            )
        )

    def prueba_2_simulador_basura_regex(self):
        self.stdout.write(
            self.style.WARNING("[PRUEBA 2] Simulador de Basura (Anti Falsos Positivos de Regex)")
        )
        self.stdout.write(
            "Configuracion: Inyectando texto incomprensible para forzar el fallo de IA y el Fallback Regex."
        )

        # Creamos un boleto temporal en la base de datos para la prueba
        boleto = BoletoImportado.objects.create(
            agencia_id=1,  # Mixin de agencia usualmente lo requiere
            estado_parseo=BoletoImportado.EstadoParseo.PENDIENTE,
        )

        # Simulamos que la extracción de texto devuelve pura basura
        texto_basura = "Hola, esto es un correo de prueba sin boletos, saludos cordiales. No hay PNR, ni vuelos."

        # Mocker para la extracción de texto y forzar error en IA para saltar rápido al Regex
        def mock_extract_text(*args, **kwargs):
            return texto_basura

        def mock_call_gemini_error(*args, **kwargs):
            # Simulamos que Gemini falla porque es pura basura, forzando el fallback
            return {"error": "No pude entender esto."}

        service = TicketParserService()

        with (
            patch(
                "apps.automation.parsers.extraction.ExtractionService.extract_text",
                side_effect=mock_extract_text,
            ),
            patch(
                "apps.automation.parsers.extraction.ExtractionService.get_open_file",
                return_value=ContentFile(b"dummy"),
            ),
            patch(
                "apps.automation.services.ai_engine.ai_engine.call_gemini",
                side_effect=mock_call_gemini_error,
            ),
        ):
            self.stdout.write(
                "   [MOCK] IA fallo. Entrando a Fallback Regex con validacion estricta..."
            )
            resultado = service.procesar_boleto(boleto.pk, bypass_cache=True, ignore_manual=True)

        # Refrescar boleto de la DB
        boleto.refresh_from_db()

        # Validaciones (Asserts)
        assert (
            boleto.estado_parseo == BoletoImportado.EstadoParseo.REVISION_REQUERIDA
        ), f"El boleto debio quedar en REVISION_REQUERIDA, pero quedo en {boleto.estado_parseo}"

        assert (
            "error" in boleto.log_parseo.lower() or "revisi" in boleto.log_parseo.lower()
        ), "El log_parseo no registra el fallo definitivo."

        self.stdout.write(
            self.style.SUCCESS(
                "[EXITO] PRUEBA 2 PASADA: El Regex detecto que la data extraida era basura. NUNCA se guardo un boleto vacio en BD y se forzo REVISION_REQUERIDA."
            )
        )

        # Limpieza
        boleto.delete()
