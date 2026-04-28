# tests/test_translator_api.py

import json
import pytest
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from core.models_catalogos import Aerolinea, Pais


class TranslatorAPITestCase(TestCase):
    """Pruebas para las APIs del traductor de itinerarios."""
    
    def setUp(self):
        """Configuración inicial para las pruebas."""
        self.client = APIClient()
        
        # Crear usuario de prueba
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        # Crear país y aerolínea de prueba
        self.pais = Pais.objects.create(
            nombre='Estados Unidos',
            codigo_iso_2='US',
            codigo_iso_3='USA'
        )
        
        self.aerolinea = Aerolinea.objects.create(
            codigo_iata='AA',
            nombre='American Airlines',
            pais=self.pais,
            activa=True
        )
        
        # Autenticar cliente
        self.client.force_authenticate(user=self.user)
    
    def test_translate_itinerary_success(self):
        """Prueba traducción exitosa de itinerario."""
        url = reverse('core:translator:translate_itinerary')
        data = {
            'itinerary': '1 AA 1234 15JAN W MIABOG 0800 1200',
            'gds_system': 'SABRE'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('translated_itinerary', response.data)
        self.assertEqual(response.data['gds_system'], 'SABRE')
    
    def test_translate_itinerary_empty(self):
        """Prueba traducción con itinerario vacío."""
        url = reverse('core:translator:translate_itinerary')
        data = {
            'itinerary': '',
            'gds_system': 'SABRE'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_calculate_ticket_price_success(self):
        """Prueba cálculo exitoso de precio de boleto."""
        url = reverse('core:translator:calculate_price')
        data = {
            'tarifa': 100.0,
            'fee_consolidador': 25.0,
            'fee_interno': 15.0,
            'porcentaje': 10.0
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('calculation', response.data)\n        \n        calculation = response.data['calculation']\n        self.assertEqual(calculation['tarifa'], 100.0)\n        self.assertEqual(calculation['suma_base'], 140.0)  # 100 + 25 + 15\n        self.assertEqual(calculation['precio_final'], 154.0)  # 140 + 10%\n    \n    def test_calculate_ticket_price_negative_values(self):\n        \"\"\"Prueba cálculo con valores negativos.\"\"\"\n        url = reverse('core:translator:calculate_price')\n        data = {\n            'tarifa': -100.0,\n            'fee_consolidador': 25.0,\n            'fee_interno': 15.0,\n            'porcentaje': 10.0\n        }\n        \n        response = self.client.post(url, data, format='json')\n        \n        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)\n        self.assertIn('error', response.data)\n    \n    def test_get_supported_gds(self):\n        \"\"\"Prueba obtención de sistemas GDS soportados.\"\"\"\n        url = reverse('core:translator:supported_gds')\n        \n        response = self.client.get(url)\n        \n        self.assertEqual(response.status_code, status.HTTP_200_OK)\n        self.assertTrue(response.data['success'])\n        self.assertIn('supported_gds', response.data)\n        \n        gds_codes = [gds['code'] for gds in response.data['supported_gds']]\n        self.assertIn('SABRE', gds_codes)\n        self.assertIn('AMADEUS', gds_codes)\n        self.assertIn('KIU', gds_codes)\n    \n    def test_get_airlines_catalog(self):\n        \"\"\"Prueba obtención del catálogo de aerolíneas.\"\"\"\n        url = reverse('core:translator:airlines_catalog')\n        \n        response = self.client.get(url)\n        \n        self.assertEqual(response.status_code, status.HTTP_200_OK)\n        self.assertTrue(response.data['success'])\n        self.assertIn('airlines', response.data)\n        self.assertGreater(response.data['total'], 0)\n        \n        # Verificar que nuestra aerolínea de prueba está incluida\n        airline_codes = [airline['code'] for airline in response.data['airlines']]\n        self.assertIn('AA', airline_codes)\n    \n    def test_get_airports_catalog(self):\n        \"\"\"Prueba obtención del catálogo de aeropuertos.\"\"\"\n        url = reverse('core:translator:airports_catalog')\n        \n        response = self.client.get(url)\n        \n        self.assertEqual(response.status_code, status.HTTP_200_OK)\n        self.assertTrue(response.data['success'])\n        self.assertIn('airports', response.data)\n        self.assertGreater(response.data['total'], 0)\n    \n    def test_validate_itinerary_format_valid(self):\n        \"\"\"Prueba validación de formato válido.\"\"\"\n        url = reverse('core:translator:validate_format')\n        data = {\n            'itinerary': '1 AA 1234 15JAN W MIABOG 0800 1200',\n            'gds_system': 'SABRE'\n        }\n        \n        response = self.client.post(url, data, format='json')\n        \n        self.assertEqual(response.status_code, status.HTTP_200_OK)\n        self.assertTrue(response.data['success'])\n        self.assertIn('validation', response.data)\n    \n    def test_validate_itinerary_format_invalid(self):\n        \"\"\"Prueba validación de formato inválido.\"\"\"\n        url = reverse('core:translator:validate_format')\n        data = {\n            'itinerary': 'formato completamente incorrecto',\n            'gds_system': 'SABRE'\n        }\n        \n        response = self.client.post(url, data, format='json')\n        \n        self.assertEqual(response.status_code, status.HTTP_200_OK)\n        self.assertTrue(response.data['success'])\n        validation = response.data['validation']\n        self.assertFalse(validation['is_valid'])\n        self.assertGreater(len(validation['invalid_lines']), 0)\n    \n    def test_batch_translate_success(self):\n        \"\"\"Prueba traducción en lote exitosa.\"\"\"\n        url = reverse('core:translator:batch_translate')\n        data = {\n            'itineraries': [\n                {\n                    'id': 'test1',\n                    'itinerary': '1 AA 1234 15JAN W MIABOG 0800 1200',\n                    'gds_system': 'SABRE'\n                },\n                {\n                    'id': 'test2',\n                    'itinerary': '2 UA 5678 16JAN W BOGMIA 1400 1800',\n                    'gds_system': 'SABRE'\n                }\n            ]\n        }\n        \n        response = self.client.post(url, data, format='json')\n        \n        self.assertEqual(response.status_code, status.HTTP_200_OK)\n        self.assertTrue(response.data['success'])\n        self.assertIn('summary', response.data)\n        self.assertIn('results', response.data)\n        \n        summary = response.data['summary']\n        self.assertEqual(summary['total'], 2)\n        self.assertEqual(len(response.data['results']), 2)\n    \n    def test_batch_translate_limit_exceeded(self):\n        \"\"\"Prueba límite de itinerarios en lote.\"\"\"\n        url = reverse('core:translator:batch_translate')\n        \n        # Crear más de 10 itinerarios\n        itineraries = []\n        for i in range(11):\n            itineraries.append({\n                'id': f'test{i}',\n                'itinerary': f'{i} AA 123{i} 15JAN W MIABOG 0800 1200',\n                'gds_system': 'SABRE'\n            })\n        \n        data = {'itineraries': itineraries}\n        \n        response = self.client.post(url, data, format='json')\n        \n        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)\n        self.assertIn('error', response.data)\n    \n    def test_batch_translate_empty_list(self):\n        \"\"\"Prueba traducción en lote con lista vacía.\"\"\"\n        url = reverse('core:translator:batch_translate')\n        data = {'itineraries': []}\n        \n        response = self.client.post(url, data, format='json')\n        \n        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)\n        self.assertIn('error', response.data)\n    \n    def test_unauthenticated_access(self):\n        \"\"\"Prueba acceso sin autenticación.\"\"\"\n        # Desautenticar cliente\n        self.client.force_authenticate(user=None)\n        \n        url = reverse('core:translator:translate_itinerary')\n        data = {\n            'itinerary': '1 AA 1234 15JAN W MIABOG 0800 1200',\n            'gds_system': 'SABRE'\n        }\n        \n        response = self.client.post(url, data, format='json')\n        \n        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)\n\n\n@pytest.mark.django_db\nclass TestTranslatorAPIIntegration:\n    \"\"\"Pruebas de integración para las APIs del traductor.\"\"\"\n    \n    def test_full_workflow(self, api_client, authenticated_user):\n        \"\"\"Prueba flujo completo de traducción.\"\"\"\n        # 1. Obtener sistemas GDS soportados\n        gds_response = api_client.get('/api/translator/gds/')\n        assert gds_response.status_code == 200\n        \n        # 2. Validar formato de itinerario\n        validate_response = api_client.post('/api/translator/validate/', {\n            'itinerary': '1 AA 1234 15JAN W MIABOG 0800 1200',\n            'gds_system': 'SABRE'\n        })\n        assert validate_response.status_code == 200\n        \n        # 3. Traducir itinerario\n        translate_response = api_client.post('/api/translator/itinerary/', {\n            'itinerary': '1 AA 1234 15JAN W MIABOG 0800 1200',\n            'gds_system': 'SABRE'\n        })\n        assert translate_response.status_code == 200\n        \n        # 4. Calcular precio\n        price_response = api_client.post('/api/translator/calculate/', {\n            'tarifa': 100.0,\n            'fee_consolidador': 25.0,\n            'fee_interno': 15.0,\n            'porcentaje': 10.0\n        })\n        assert price_response.status_code == 200