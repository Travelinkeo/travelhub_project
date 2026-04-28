from datetime import datetime
from types import SimpleNamespace

import pytest

from core import pdf_generator


class DummyTemplate:
    def __init__(self, marker):
        self.marker = marker
    def render(self, ctx):  # pragma: no cover - trivial
        # Insert marker so we can assert dispatch logic indirectly if needed
        return f"<html><body>{self.marker}</body></html>"

class DummyEnv:
    def __init__(self):
        self.requested = []
    def get_template(self, name):
        self.requested.append(name)
        return DummyTemplate(name)

@pytest.mark.parametrize(
    'source_system,expected_template', [
        ('SABRE', 'tickets/ticket_template_sabre.html'),
        ('AMADEUS', 'tickets/ticket_template_amadeus.html'),
        ('TRAVELPORT', 'tickets/ticket_template_travelport.html'),
        ('KIU', 'tickets/ticket_template_kiu.html'),
        (None, 'tickets/ticket_template_kiu.html'),
    ]
)
def test_select_template_and_data(source_system, expected_template, monkeypatch):
    env = DummyEnv()
    data = {'SOURCE_SYSTEM': source_system} if source_system else {}
    # provide minimal required keys to avoid KeyErrors
    template, template_data = pdf_generator.select_template_and_data(data, env)
    assert env.requested[0] == expected_template
    assert 'logo_base64' in template_data
    assert template is not None


def test_build_ticket_filename_deterministic():
    fixed = datetime(2025, 1, 2, 3, 4, 5)
    name = pdf_generator.build_ticket_filename('308-0201196996', when=fixed)
    assert name == 'Boleto_308-0201196996_20250102030405.pdf'


def test_build_ticket_filename_sanitize(): 
    fixed = datetime(2025, 1, 2, 3, 4, 5) 
    # Include espacios y caracteres ilegales: / * ? : " < > | que deben eliminarse 
    raw = '  30 8/*?:"<>| bad ' 
    name = pdf_generator.build_ticket_filename(raw, when=fixed) 
    # Esperado: caracteres prohibidos removidos, espacios -> _ , preserva letras 
    assert name == 'Boleto_30_8_bad_20250102030405.pdf'


def test_generate_ticket_pdf_mocks_weasyprint(monkeypatch):
    # Replace HTML class to avoid real PDF generation
    class FakeHTML:
        def __init__(self, string):
            self.string = string
        def write_pdf(self, stylesheets=None):
            return b'%PDF-fake%'
    monkeypatch.setattr(pdf_generator, 'HTML', FakeHTML)

    # Monkeypatch Environment to our dummy
    def fake_environment(*args, **kwargs):
        return SimpleNamespace(get_template=lambda n: DummyTemplate(n))
    monkeypatch.setattr(pdf_generator, 'Environment', fake_environment)

    data = {'SOURCE_SYSTEM': 'SABRE', 'numero_boleto': '1234567890'}
    pdf_bytes, filename = pdf_generator.generate_ticket_pdf(data)
    assert pdf_bytes.startswith(b'%PDF-fake%')
    assert filename.startswith('Boleto_1234567890_') and filename.endswith('.pdf')


def test_transform_sabre_data_for_template_basic():
    raw = {
        'preparado_para': 'John Doe',
        'documento_identidad': 'AB123',
        'numero_boleto': '123',
        'vuelos': [
            {
                'fecha_salida': '2025-01-01',
                'fecha_llegada': '2025-01-01',
                'aerolinea': 'XX',
                'numero_vuelo': 'XX101',
                'otras_notas': 'PNR ABCDEF',
                'aeropuerto_salida': 'Caracas, Venezuela',
                'aeropuerto_llegada': 'Panama, Panama'
            }
        ]
    }
    norm = pdf_generator.transform_sabre_data_for_template(raw)
    assert norm['pasajero']['nombre_completo'] == 'John Doe'
    assert norm['itinerario']['vuelos'][0]['origen']['ciudad'] == 'Caracas'
    assert norm['itinerario']['vuelos'][0]['destino']['pais'] == 'Panama'
