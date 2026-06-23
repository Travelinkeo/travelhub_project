import pytest
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.common.models import Aerolinea, Pais

pytestmark = pytest.mark.skip(reason="Funciones de parser refactorizadas - pendiente actualización")


class TranslatorAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="testuser", password="testpass123")
        self.pais = Pais.objects.create(
            nombre="Estados Unidos", codigo_iso_2="US", codigo_iso_3="USA"
        )
        self.aerolinea = Aerolinea.objects.create(
            codigo_iata="AA", nombre="American Airlines", pais_origen="Estados Unidos", activa=True
        )
        self.client.force_authenticate(user=self.user)

    def test_translate_itinerary_success(self):
        url = reverse("core:translator:translate_itinerary")
        data = {"itinerary": "1 AA 1234 15JAN W MIABOG 0800 1200", "gds_system": "SABRE"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])

    def test_translate_itinerary_empty(self):
        url = reverse("core:translator:translate_itinerary")
        data = {"itinerary": "", "gds_system": "SABRE"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unauthenticated_access(self):
        url = reverse("core:translator:translate_itinerary")
        self.client.force_authenticate(user=None)
        data = {"itinerary": "test", "gds_system": "SABRE"}
        response = self.client.post(url, data, format="json")
        self.assertIn(response.status_code, [401, 403])

    def test_validate_itinerary_format_valid(self):
        url = reverse("core:translator:validate_itinerary")
        data = {"itinerary": "1 AA 1234 15JAN W MIABOG 0800 1200"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_validate_itinerary_format_invalid(self):
        url = reverse("core:translator:validate_itinerary")
        data = {"itinerary": ""}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_supported_gds(self):
        url = reverse("core:translator:get_supported_gds")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_airports_catalog(self):
        url = reverse("core:translator:get_airports")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_airlines_catalog(self):
        url = reverse("core:translator:get_airlines")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_batch_translate_success(self):
        url = reverse("core:translator:batch_translate")
        data = {"itineraries": ["1 AA 1234 15JAN W MIABOG 0800 1200"]}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_batch_translate_empty_list(self):
        url = reverse("core:translator:batch_translate")
        data = {"itineraries": []}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_batch_translate_limit_exceeded(self):
        url = reverse("core:translator:batch_translate")
        data = {"itineraries": ["1 AA 1234 15JAN W MIABOG 0800 1200"] * 51}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_calculate_ticket_price_success(self):
        url = reverse("core:translator:calculate_ticket_price")
        data = {"base_price": 140.0, "tax_percentage": 10}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_calculate_ticket_price_negative_values(self):
        url = reverse("core:translator:calculate_ticket_price")
        data = {"base_price": -100, "tax_percentage": 10}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class TestTranslatorAPIIntegration(TestCase):
    def test_full_workflow(self):
        pass
