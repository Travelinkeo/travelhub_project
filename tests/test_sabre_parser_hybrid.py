
import os
import unittest

from core.ticket_parser import extract_data_from_text


class TestHybridSabreParser(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Carga el contenido del fixture de texto una vez para todas las pruebas de la clase."""
        fixture_path = os.path.join(os.path.dirname(__file__), 'fixtures', 'sabre_rosangela_diaz_fixture.txt')
        try:
            with open(fixture_path, encoding='utf-8') as f:
                cls.fixture_text = f.read()
        except FileNotFoundError as err:
            raise unittest.SkipTest(f"No se encontró el archivo fixture en {fixture_path}. Salteando pruebas.") from err

    def test_full_sabre_ticket_parsing(self):
        """
        Prueba el parseo completo de un boleto de Sabre a partir del fixture de texto.
        Verifica que los campos clave se extraen y normalizan correctamente.
        """
        self.assertIsNotNone(self.fixture_text, "El fixture de texto no se cargó correctamente.")

        # Llamar a la función principal de parseo
        parsed_data = extract_data_from_text(self.fixture_text)

        # Verificar que no hay errores y que el sistema fuente es SABRE
        self.assertNotIn('error', parsed_data)
        self.assertEqual(parsed_data.get('SOURCE_SYSTEM'), 'SABRE')

        # Verificar campos clave del nivel superior
        self.assertEqual(parsed_data.get('codigo_reservacion'), 'SGWFJU')
        self.assertEqual(parsed_data.get('numero_boleto'), '3317182983297')
        self.assertEqual(parsed_data.get('preparado_para'), 'DIAZ SILVA/ROSANGELA')
        self.assertEqual(parsed_data.get('documento_identidad'), '164271115')
        self.assertEqual(parsed_data.get('aerolinea_emisora'), 'SATA INTERNATIONAL SERVI')
        self.assertEqual(parsed_data.get('fecha_emision_iso'), '2025-02-25')

        # Verificar la normalización
        normalized_data = parsed_data.get('normalized', {})
        self.assertEqual(normalized_data.get('ticket_number'), '3317182983297')
        self.assertEqual(normalized_data.get('reservation_code'), 'SGWFJU')
        self.assertEqual(normalized_data.get('passenger_name'), 'ROSANGELA DIAZ SILVA')
        self.assertEqual(normalized_data.get('airline_name'), 'SATA INTERNATIONAL SERVI')

        # Verificar la estructura del itinerario
        vuelos = parsed_data.get('vuelos', [])
        self.assertEqual(len(vuelos), 2, "Deberían haberse encontrado exactamente 2 vuelos.")

        # Verificar detalles del primer vuelo
        vuelo_1 = vuelos[0]
        self.assertEqual(vuelo_1.get('numero_vuelo'), 'S48015')
        self.assertEqual(vuelo_1.get('fecha_salida_iso'), '2025-03-19')
        self.assertEqual(vuelo_1['origen']['ciudad'], 'LISBON, PORTUGAL')
        self.assertEqual(vuelo_1['destino']['ciudad'], 'FUNCHAL, PORTUGAL')
        self.assertEqual(vuelo_1.get('hora_salida'), '18:40')
        self.assertEqual(vuelo_1.get('hora_llegada'), '20:25')

        # Verificar detalles del segundo vuelo
        vuelo_2 = vuelos[1]
        self.assertEqual(vuelo_2.get('numero_vuelo'), 'S48294')
        self.assertEqual(vuelo_2.get('fecha_salida_iso'), '2025-03-23')
        self.assertEqual(vuelo_2['origen']['ciudad'], 'FUNCHAL, PORTUGAL')
        self.assertEqual(vuelo_2['destino']['ciudad'], 'PORTO, PORTUGAL')
        self.assertEqual(vuelo_2.get('hora_salida'), '08:45')
        self.assertEqual(vuelo_2.get('hora_llegada'), '10:40')

if __name__ == '__main__':
    unittest.main()
