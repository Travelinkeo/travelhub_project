from unittest.mock import patch

import pytest

from apps.bookings.models import Venta
from apps.bookings.services.pnr_parser_service import PNRParserService


@pytest.mark.django_db
class TestMotorGdsParser:
    @patch("apps.bookings.tasks.verificar_cumplimiento_pasaportes_reserva_task.delay")
    def test_parseo_exitoso_pnr_amadeus(self, mock_delay, agencia_premium):
        """Simula la ingesta headless de un string críptico real de Amadeus."""
        raw_pnr_amadeus = (
            "RP/CCSM121A0/CCSM121A0              22MAY26/1335Z   S8X3J9\n"
            " 1.ALEMAN/JOSE ARMANDO\n"
            " 2  LH 535 Y 15OCT CCSFRA HK1  1655 0930+1\n"
            " 3  LH 112 Y 16OCT FRAMAD HK1  1100 1315\n"
            "APE CC CARACAS TRAVELHUB OFFICE\n"
            "TK OK22MAY/CCSM121A0"
        )

        # Ejecutamos la ingesta atómica pasándole el tenant
        venta = PNRParserService.ingerir_pnr_en_db(raw_pnr_amadeus, agencia_premium)

        # Validaciones de integridad de datos
        assert venta.localizador == "S8X3J9"
        assert venta.canal_origen == Venta.CanalOrigen.API
        assert venta.agencia == agencia_premium

        # Validar indexación automática en el CRM de Pasajeros
        assert venta.pasajeros.count() == 1
        pasajero = venta.pasajeros.first()
        assert pasajero.apellidos == "ALEMAN"
        assert pasajero.nombres == "JOSE ARMANDO"
