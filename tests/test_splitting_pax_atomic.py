from unittest.mock import patch

import pytest
from django.db import connection

from apps.automation.services.ticket_parser_service import TicketParserService
from apps.bookings.models import BoletoImportado, BoletoImportadoTransito
from core.models import Agencia


@pytest.mark.django_db(transaction=True)
class TestSplittingPaxAtomic:
    def test_multi_pax_split_success(self):
        # Setup agency
        agencia = Agencia.objects.create(nombre="Agencia Test", email_principal="test@agency.com")

        # Setup source BoletoImportado
        # Use _skip_auto_parse to avoid eager Celery triggering during creation
        boleto = BoletoImportado(
            archivo_boleto="test_ticket.txt", agencia=agencia, estado_parseo="PEN"
        )
        boleto._skip_auto_parse = True
        boleto.save()

        # Mock GDS response for multi-passenger
        mock_data = {
            "is_multi_pax": True,
            "tickets": [
                {
                    "passenger_name": "ISAZA/MAURICIO",
                    "ticket_number": "1347258019382",
                    "pnr": "WPYVSD",
                    "carrier": "AV",
                    "issuing_airline": "AVIANCA",
                    "tarifa_base": 800.0,
                    "impuestos": 150.0,
                    "total": 950.0,
                    "segments": [
                        {
                            "flight_number": "AV46",
                            "departure": "BOG",
                            "arrival": "MAD",
                            "departure_date": "2026-05-22",
                        }
                    ],
                },
                {
                    "passenger_name": "ISAZA/JUAN",
                    "ticket_number": "1347258019383",
                    "pnr": "WPYVSD",
                    "carrier": "AV",
                    "issuing_airline": "AVIANCA",
                    "tarifa_base": 800.0,
                    "impuestos": 150.0,
                    "total": 950.0,
                    "segments": [
                        {
                            "flight_number": "AV46",
                            "departure": "BOG",
                            "arrival": "MAD",
                            "departure_date": "2026-05-22",
                        }
                    ],
                },
            ],
        }

        # Instantiate service
        service = TicketParserService()

        with (
            patch(
                "apps.automation.services.ticket_parser_service.ExtractionService.extract_text",
                return_value="some dummy ticket text",
            ),
            patch(
                "apps.automation.parsers.ai_universal_parser.UniversalAIParser.parse",
                return_value=mock_data,
            ),
            patch("apps.common.utils.celery_utils.safe_delay") as mock_safe_delay,
        ):
            # Run pipeline
            venta = service._run_pipeline(boleto.pk, forced_client_id=None, ignore_manual=False)

            # Assertions
            assert venta is not None

            # Manually trigger on_commit hooks since standard test transaction won't commit
            connection.run_and_clear_commit_hooks()

            # Verify transit table contains both staged and marked as processed
            transit_records = BoletoImportadoTransito.objects.filter(boleto_origen=boleto)
            assert transit_records.count() == 2
            assert all(tr.procesado for tr in transit_records)

            # Verify BoletoImportado created for extra passengers
            all_boletos = BoletoImportado.objects.filter(agencia=agencia)
            # 1 original + 1 additional
            assert all_boletos.count() == 2

            # Verify Celery PDF task registration
            assert mock_safe_delay.call_count >= 1

    def test_multi_pax_split_atomic_rollback(self):
        agencia = Agencia.objects.create(
            nombre="Agencia Rollback", email_principal="rollback@agency.com"
        )

        # Setup source BoletoImportado
        # Use _skip_auto_parse to avoid eager Celery triggering during creation
        boleto = BoletoImportado(
            archivo_boleto="test_ticket_rollback.txt", agencia=agencia, estado_parseo="PEN"
        )
        boleto._skip_auto_parse = True
        boleto.save()

        mock_data = {
            "is_multi_pax": True,
            "tickets": [
                {
                    "passenger_name": "ISAZA/MAURICIO",
                    "ticket_number": "1347258019382",
                    "pnr": "WPYVSD",
                },
                {"passenger_name": "ISAZA/JUAN", "ticket_number": "1347258019383", "pnr": "WPYVSD"},
            ],
        }

        service = TicketParserService()

        # Force process_single_ticket to throw an error on the second ticket
        original_process = service._process_single_ticket

        def side_effect(b, data, client_id):
            if data.get("passenger_name") == "ISAZA/JUAN" or (
                b.estado_parseo == "PEN" and b.pk != boleto.pk
            ):
                raise ValueError("Simulated splitting error for atomicity check")
            return original_process(b, data, client_id)

        with (
            patch(
                "apps.automation.services.ticket_parser_service.ExtractionService.extract_text",
                return_value="some dummy ticket text",
            ),
            patch(
                "apps.automation.parsers.ai_universal_parser.UniversalAIParser.parse",
                return_value=mock_data,
            ),
            patch.object(service, "_process_single_ticket", side_effect=side_effect),
        ):
            service._run_pipeline(boleto.pk, forced_client_id=None, ignore_manual=False)

            # Verify transit records rolled back completely because of the outer atomic transaction block!
            assert BoletoImportadoTransito.objects.filter(boleto_origen=boleto).count() == 0

            # Only the original boleto exists, and it is marked as REV or ERR
            assert BoletoImportado.objects.filter(agencia=agencia).count() == 1
            boleto.refresh_from_db()
            assert boleto.estado_parseo in ("REV", "ERR")
