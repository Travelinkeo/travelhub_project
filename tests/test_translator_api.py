# tests/test_translator_api.py

import json
import pytest
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from apps.common.models import Aerolinea, Pais


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
        self.assertIn('calculation', response.data)
        
        calculation = response.data['calculation']
        self.assertEqual(calculation['tarifa'], 100.0)
        self.assertEqual(calculation['suma_base'], 140.0)  # 100 + 25 + 15
        self.assertEqual(calculation['precio_final'], 154.0)  # 140 + 10%
    
    def test_calculate_ticket_price_negative_values(self):
        """Prueba cálculo con valores negativos."""
        url = reverse('core:translator:calculate_price')
        data = {
            'tarifa': -100.0,
            'fee_consolidador': 25.0,
            'fee_interno': 15.0,
            'porcentaje': 10.0
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_get_supported_gds(self):
        """Prueba obtención de sistemas GDS soportados."""
        url = reverse('core:translator:supported_gds')
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('supported_gds', response.data)
        
        gds_codes = [gds['code'] for gds in response.data['supported_gds']]
        self.assertIn('SABRE', gds_codes)
        self.assertIn('AMADEUS', gds_codes)
        self.assertIn('KIU', gds_codes)
    
    def test_get_airlines_catalog(self):
        """Prueba obtención del catálogo de aerolíneas."""
        url = reverse('core:translator:airlines_catalog')
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('airlines', response.data)
        self.assertGreater(response.data['total'], 0)
        
        # Verificar que nuestra aerolínea de prueba está incluida
        airline_codes = [airline['code'] for airline in response.data['airlines']]
        self.assertIn('AA', airline_codes)
    
    def test_get_airports_catalog(self):
        """Prueba obtención del catálogo de aeropuertos."""
        url = reverse('core:translator:airports_catalog')
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('airports', response.data)
        self.assertGreater(response.data['total'], 0)
    
    def test_validate_itinerary_format_valid(self):
        """Prueba validación de formato válido."""
        url = reverse('core:translator:validate_format')
        data = {
            'itinerary': '1 AA 1234 15JAN W MIABOG 0800 1200',
            'gds_system': 'SABRE'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('validation', response.data)
    
    def test_validate_itinerary_format_invalid(self):
        """Prueba validación de formato inválido."""
        url = reverse('core:translator:validate_format')
        data = {
            'itinerary': 'formato completamente incorrecto',
            'gds_system': 'SABRE'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        validation = response.data['validation']
        self.assertFalse(validation['is_valid'])
        self.assertGreater(len(validation['invalid_lines']), 0)
    
    def test_batch_translate_success(self):
        """Prueba traducción en lote exitosa."""
        url = reverse('core:translator:batch_translate')
        data = {
            'itineraries': [
                {
                    'id': 'test1',
                    'itinerary': '1 AA 1234 15JAN W MIABOG 0800 1200',
                    'gds_system': 'SABRE'
                },
                {
                    'id': 'test2',
                    'itinerary': '2 UA 5678 16JAN W BOGMIA 1400 1800',
                    'gds_system': 'SABRE'
                }
            ]
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('summary', response.data)
        self.assertIn('results', response.data)
        
        summary = response.data['summary']
        self.assertEqual(summary['total'], 2)
        self.assertEqual(len(response.data['results']), 2)
    
    def test_batch_translate_limit_exceeded(self):
        """Prueba límite de itinerarios en lote."""
        url = reverse('core:translator:batch_translate')
        
        # Crear más de 10 itinerarios
        itineraries = []
        for i in range(11):
            itineraries.append({
                'id': f'test{i}',
                'itinerary': f'{i} AA 123{i} 15JAN W MIABOG 0800 1200',
                'gds_system': 'SABRE'
            })
        
        data = {'itineraries': itineraries}
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_batch_translate_empty_list(self):
        """Prueba traducción en lote con lista vacía."""
        url = reverse('core:translator:batch_translate')
        data = {'itineraries': []}
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_unauthenticated_access(self):
        """Prueba acceso sin autenticación."""
        # Desautenticar cliente
        self.client.force_authenticate(user=None)
        
        url = reverse('core:translator:translate_itinerary')
        data = {
            'itinerary': '1 AA 1234 15JAN W MIABOG 0800 1200',
            'gds_system': 'SABRE'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


@pytest.mark.django_db
class TestTranslatorAPIIntegration:
    """Pruebas de integración para las APIs del traductor."""
    
    def test_full_workflow(self, api_client, authenticated_user):
        """Prueba flujo completo de traducción."""
        # 1. Obtener sistemas GDS soportados
        gds_response = api_client.get('/api/translator/gds/')
        assert gds_response.status_code == 200
        
        # 2. Validar formato de itinerario
        validate_response = api_client.post('/api/translator/validate/', {
            'itinerary': '1 AA 1234 15JAN W MIABOG 0800 1200',
            'gds_system': 'SABRE'
        })
        assert validate_response.status_code == 200
        
        # 3. Traducir itinerario
        translate_response = api_client.post('/api/translator/itinerary/', {
            'itinerary': '1 AA 1234 15JAN W MIABOG 0800 1200',
            'gds_system': 'SABRE'
        })
        assert translate_response.status_code == 200
        
        # 4. Calcular precio
        price_response = api_client.post('/api/translator/calculate/', {
            'tarifa': 100.0,
            'fee_consolidador': 25.0,
            'fee_interno': 15.0,
            'porcentaje': 10.0
        })
        assert price_response.status_code == 200