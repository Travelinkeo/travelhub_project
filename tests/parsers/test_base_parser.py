"""Tests para BaseTicketParser"""

from decimal import Decimal

from apps.automation.parsers.base_parser import ParsedTicketData
from apps.automation.parsers.legacy.sabre_parser import SabreParser


class TestBaseParserMethods:
    """Tests para métodos comunes de BaseTicketParser"""

    def test_extract_currency_amount_usd(self):
        """test_extract_currency_amount_usd."""
        parser = SabreParser()
        currency, amount = parser.extract_currency_amount("USD 1,234.56")
        assert currency == "USD"
        assert amount == Decimal("1234.56")

    def test_extract_currency_amount_eur(self):
        """test_extract_currency_amount_eur."""
        parser = SabreParser()
        currency, amount = parser.extract_currency_amount("EUR 500.00")
        assert currency == "EUR"
        assert amount == Decimal("500.00")

    def test_extract_currency_amount_no_match(self):
        """test_extract_currency_amount_no_match."""
        parser = SabreParser()
        currency, amount = parser.extract_currency_amount("No encontrado")
        assert currency is None
        assert amount is None

    def test_clean_text(self):
        """test_clean_text."""
        parser = SabreParser()
        result = parser.clean_text("  Multiple   spaces   ")
        assert result == "Multiple spaces"

    def test_purify_text_for_detection(self):
        """test_purify_text_for_detection."""
        parser = SabreParser()
        result = parser.purify_text_for_detection("  <p>Some   HTML   &nbsp; elements</p>   ")
        assert result == "SOME HTML ELEMENTS"

    def test_extract_field_first_pattern(self):
        """test_extract_field_first_pattern."""
        parser = SabreParser()
        text = "Reservation Code: ABC123"
        result = parser.extract_field(
            text, [r"Reservation Code:\s*([A-Z0-9]+)", r"PNR:\s*([A-Z0-9]+)"]
        )
        assert result == "ABC123"

    def test_extract_field_second_pattern(self):
        """test_extract_field_second_pattern."""
        parser = SabreParser()
        text = "PNR: XYZ789"
        result = parser.extract_field(
            text, [r"Reservation Code:\s*([A-Z0-9]+)", r"PNR:\s*([A-Z0-9]+)"]
        )
        assert result == "XYZ789"

    def test_extract_field_no_match(self):
        """test_extract_field_no_match."""
        parser = SabreParser()
        text = "Some random text"
        result = parser.extract_field(text, [r"PNR:\s*([A-Z0-9]+)"])
        assert result == "No encontrado"


class TestResolveIataFromCity:
    """Tests para DataNormalizationService._resolve_iata_from_city.

    Estos tests NO requieren DB: el método usa solo índices pre-cargados en
    memoria (airports_master) + alias manuales. Garantizan que el parser no se
    quede a ciegas cuando el GDS imprime el NOMBRE de la ciudad en lugar del
    código IATA (caso Turpial/Estelar en rutas domésticas Venezolanas).
    """

    def test_resolve_alias_san_antonio_to_svz(self):
        """San Antonio (VE, Turpial) debe resolver a SVZ, NO a Texas/US."""
        from apps.automation.parsers.normalization import DataNormalizationService

        assert DataNormalizationService._resolve_iata_from_city("SAN ANTONIO") == "SVZ"

    def test_resolve_alias_valencia_to_vln(self):
        """Valencia (VE) debe resolver a VLN, NO a VLC (España)."""
        from apps.automation.parsers.normalization import DataNormalizationService

        assert DataNormalizationService._resolve_iata_from_city("VALENCIA") == "VLN"

    def test_resolve_alias_santo_domingo_to_std(self):
        """test_resolve_alias_santo_domingo_to_std."""
        from apps.automation.parsers.normalization import DataNormalizationService

        assert DataNormalizationService._resolve_iata_from_city("SANTO DOMINGO") == "STD"

    def test_resolve_explicit_3_letter_iata_passes_through(self):
        """test_resolve_explicit_3_letter_iata_passes_through."""
        from apps.automation.parsers.normalization import DataNormalizationService

        assert DataNormalizationService._resolve_iata_from_city("MAD") == "MAD"
        assert DataNormalizationService._resolve_iata_from_city("BOG") == "BOG"

    def test_resolve_respects_current_iata_when_provided(self):
        """Si el parser ya extrajo el IATA, no se sobreescribe."""
        from apps.automation.parsers.normalization import DataNormalizationService

        assert (
            DataNormalizationService._resolve_iata_from_city("VALENCIA", current_iata="VLC")
            == "VLC"
        )

    def test_resolve_handles_city_with_country_suffix(self):
        """ "VALENCIA, VENEZUELA" debe resolverse correctamente despreciando el país."""
        from apps.automation.parsers.normalization import DataNormalizationService

        assert DataNormalizationService._resolve_iata_from_city("VALENCIA, VENEZUELA") == "VLN"

    def test_resolve_handles_city_with_state_suffix(self):
        """ "SAN ANTONIO TX" no debe machacar el alias VE con Texas."""
        from apps.automation.parsers.normalization import DataNormalizationService

        # El alias manual SVZ tiene prioridad — incluso si appended TX.
        assert DataNormalizationService._resolve_iata_from_city("SAN ANTONIO TX") == "SVZ"

    def test_resolve_empty_returns_none(self):
        """test_resolve_empty_returns_none."""
        from apps.automation.parsers.normalization import DataNormalizationService

        assert DataNormalizationService._resolve_iata_from_city("") is None
        assert DataNormalizationService._resolve_iata_from_city(None) is None

    def test_resolve_unknown_city_returns_none_not_random_iata(self):
        """Ciudad ambigua sin alias NO debe inventar un IATA incorrecto."""
        from apps.automation.parsers.normalization import DataNormalizationService

        # Springifeld existe en muchos estados — debe devolver None en lugar de
        # tomar el primer candidatoEquívoco.
        assert DataNormalizationService._resolve_iata_from_city("CIUDAD_QUE_NO_EXISTE_XYZ") is None


class TestCatalogNormalizationServiceIndices:
    """Tests para los índices O(1) de CatalogNormalizationService.

    NO requieren DB: solo verifican que los índices secundarios (airports_by_iata
    y airports_by_city) se construyen correctamente y aceleran los lookups.
    """

    def test_airports_by_iata_index_has_vln(self):
        """test_airports_by_iata_index_has_vln."""
        from apps.common.services.catalog_service import CatalogNormalizationService

        CatalogNormalizationService._load_airports()
        assert CatalogNormalizationService._airports_by_iata is not None
        assert "VLN" in CatalogNormalizationService._airports_by_iata
        assert "CCS" in CatalogNormalizationService._airports_by_iata
        assert "MAD" in CatalogNormalizationService._airports_by_iata

    def test_airports_by_city_index_has_valencia(self):
        """test_airports_by_city_index_has_valencia."""
        from apps.common.services.catalog_service import CatalogNormalizationService

        CatalogNormalizationService._load_airports()
        assert CatalogNormalizationService._airports_by_city is not None
        assert "VALENCIA" in CatalogNormalizationService._airports_by_city
        # Debe contener tanto Venezuela (VLN) como España (VLC)
        valencia_airports = CatalogNormalizationService._airports_by_city["VALENCIA"]
        iatas = {(a.get("iata") or "").upper() for a in valencia_airports if a.get("iata")}
        assert "VLN" in iatas
        assert "VLC" in iatas

    def test_get_airports_by_iata_returns_dict_or_none(self):
        """test_get_airports_by_iata_returns_dict_or_none."""
        from apps.common.services.catalog_service import CatalogNormalizationService

        info = CatalogNormalizationService._get_airports_by_iata("VLN")
        assert info is not None
        assert info["iata"] == "VLN"
        assert info["country"] == "VE"
        assert CatalogNormalizationService._get_airports_by_iata("ZZZ") is None

    def test_get_airports_by_city_returns_list(self):
        """test_get_airports_by_city_returns_list."""
        from apps.common.services.catalog_service import CatalogNormalizationService

        results = CatalogNormalizationService._get_airports_by_city("Caracas")
        assert isinstance(results, list)
        assert len(results) >= 1
        assert any((r.get("iata") or "").upper() == "CCS" for r in results)


class TestParsedTicketData:
    """Tests para ParsedTicketData"""

    def test_to_dict(self):
        """test_to_dict."""
        data = ParsedTicketData(
            source_system="TEST",
            pnr="ABC123",
            ticket_number="123456",
            passenger_name="John Doe",
            issue_date="2025-01-01",
            flights=[],
            fares={},
            raw_data={},
        )

        result = data.to_dict()
        assert result["SOURCE_SYSTEM"] == "TEST"
        assert result["pnr"] == "ABC123"
        assert result["ticket_number"] == "123456"
        assert result["passenger_name"] == "John Doe"
