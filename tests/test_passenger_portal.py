"""Tests para Passenger portal."""
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.urls import reverse

from apps.bookings.models import Venta
from apps.bookings.models.componentes import ServicioAdicionalDetalle
from apps.bookings.services.itinerary_service import ItineraryCryptoService
from apps.crm.models import Pasajero
from core.models import Agencia


@pytest.mark.django_db(transaction=True)
class TestPassengerPortal:
    """
    Tests para el Portal del Pasajero: visualización de itinerario en vivo,
    procesamiento OCR de pasaportes y solicitud de venta cruzada.
    """

    @pytest.fixture(autouse=True)
    def setup_data(self):
        """Setup data."""
        self.client = Client()

        # 1. Crear Agencia
        self.agencia = Agencia.objects.create(nombre="Test Portal Agency")

        # 2. Crear Venta
        self.venta = Venta.objects.create(
            agencia=self.agencia, localizador="WPYVSD", total_venta=150.00
        )

        # 3. Crear Pasajero y asociar
        self.pasajero = Pasajero.objects.create(
            agencia=self.agencia, nombres="MAURICIO", apellidos="ISAZA", numero_pasaporte=""
        )
        self.venta.pasajeros.add(self.pasajero)
        self.venta.save()

        # 4. Generar Token Criptográfico
        self.token = ItineraryCryptoService.generar_enlace_itinerario(self.venta).split("/")[-2]

    def test_public_itinerary_live_page_renders(self):
        """
        Verifica que la página de itinerario público se renderiza correctamente con el token.
        """
        url = reverse("bookings:public_itinerary_live", kwargs={"token": self.token})
        response = self.client.get(url)
        assert response.status_code == 200
        assert b"WPYVSD" in response.content
        assert b"MAURICIO" in response.content

    @patch("apps.automation.services.ocr_service.OCRService.procesar_pasaporte")
    def test_public_itinerary_ocr_upload(self, mock_ocr):
        """
        Verifica que la subida del pasaporte ejecuta el OCR y devuelve el HTML de verificación.
        """
        # Mocking OCR response
        mock_ocr.return_value = {
            "success": True,
            "nombres": "MAURICIO",
            "apellidos": "ISAZA",
            "numero_pasaporte": "134725801",
            "fecha_nacimiento": "1985-05-08",
            "fecha_vencimiento": "2030-05-08",
            "sexo": "M",
            "nacionalidad": "VEN",
            "pais_emision": "VEN",
            "face_image_base64": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=",
        }

        url = reverse(
            "bookings:public_itinerary_ocr_upload",
            kwargs={"token": self.token, "pasajero_id": self.pasajero.pk},
        )

        dummy_image = SimpleUploadedFile(
            "passport.jpg", b"dummy_content", content_type="image/jpeg"
        )
        response = self.client.post(
            url, {"archivo": dummy_image}, HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )

        assert response.status_code == 200
        assert b"Verificaci\xc3\xb3n de Pasaporte" in response.content
        assert b"134725801" in response.content
        mock_ocr.assert_called_once()

    def test_public_itinerary_ocr_save(self):
        """
        Verifica que la confirmación de los datos actualiza los campos del modelo Pasajero.
        """
        url = reverse(
            "bookings:public_itinerary_ocr_save",
            kwargs={"token": self.token, "pasajero_id": self.pasajero.pk},
        )

        post_data = {
            "nombres": "MAURICIO NUEVO",
            "apellidos": "ISAZA NUEVO",
            "numero_pasaporte": "999999999",
            "fecha_nacimiento": "1985-05-08",
            "fecha_vencimiento": "2030-05-08",
            "sexo": "M",
            "nacionalidad": "VEN",
            "pais_emision": "VEN",
            "face_image_base64": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=",
        }

        response = self.client.post(url, post_data)
        assert response.status_code == 200
        assert b"guardado con" in response.content

        # Verificar en base de datos
        self.pasajero.refresh_from_db()
        assert self.pasajero.nombres == "MAURICIO NUEVO"
        assert self.pasajero.apellidos == "ISAZA NUEVO"
        assert self.pasajero.numero_pasaporte == "999999999"

    def test_public_itinerary_cross_sell(self):
        """
        Verifica que la solicitud de venta cruzada crea un ServicioAdicionalDetalle en borrador.
        """
        url = reverse("bookings:public_itinerary_cross_sell", kwargs={"token": self.token})

        post_data = {
            "tipo_servicio": "SEG",
            "nombre_pasajero": "ISAZA, MAURICIO",
            "fecha_inicio": "2026-07-10",
            "fecha_fin": "2026-07-20",
            "notas": "Quiero cobertura médica premium.",
        }

        response = self.client.post(url, post_data)
        assert response.status_code == 200
        assert b"Solicitud Recibida" in response.content

        # Verificar que el servicio adicional borrador se creó correctamente
        servicios = ServicioAdicionalDetalle.objects.filter(venta=self.venta)
        assert servicios.count() == 1
        servicio = servicios.first()
        assert servicio.tipo_servicio == "SEG"
        assert servicio.costo_neto == 0
        assert servicio.precio_venta == 0
        assert "Quiero cobertura médica premium." in servicio.notas
