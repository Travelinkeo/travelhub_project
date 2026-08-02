"""
Comando de carga masiva para poblar hoteles y posadas de Venezuela desde Google Places API.

Uso:
  python manage.py poblar_hoteles_venezuela                     # Cargar hoteles en todos los destinos
  python manage.py poblar_hoteles_venezuela --destino="Margarita"  # Cargar un solo destino
  python manage.py poblar_hoteles_venezuela --max-por-destino=10 # Limitar por ciudad
  python manage.py poblar_hoteles_venezuela --dry-run
"""

import logging
import time

import requests
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from apps.bookings.models import HotelTarifario, ImagenHotel

logger = logging.getLogger(__name__)

# Destinos turísticos y ciudades principales de Venezuela
DESTINOS_VENEZUELA = [
    # Islas y Playas
    "Isla de Margarita",
    "Isla de Coche",
    "Los Roques",
    "Morrocoy",
    "Tucacas",
    "Chichirivichi",
    "Mochima",
    "Choroní",
    "La Guaira",
    "Higuerote",
    "Lechería",
    "Puerto La Cruz",
    "Cumaná",
    "Punto Fijo",
    "Coro",
    # Montaña y Turismo Ecológico
    "Mérida",
    "Colonia Tovar",
    "Canaima",
    "Gran Sabana",
    "La Puerta Trujillo",
    "El Jarillo",
    # Ciudades Principales
    "Caracas",
    "Valencia",
    "Maracaibo",
    "Barquisimeto",
    "Maracay",
    "Ciudad Guayana",
    "Puerto Ordaz",
    "San Cristóbal",
    "Maturín",
    "Barinas",
]


class Command(BaseCommand):
    """Poblar catálogo masivo de hoteles de Venezuela mediante Google Places API."""

    help = "Poblar catálogo de hoteles y posadas de Venezuela con sus fotos oficial de Google Places API"

    def add_arguments(self, parser):
        """add_arguments."""
        parser.add_argument("--destino", type=str, default=None, help="Filtrar un solo destino")
        parser.add_argument(
            "--max-por-destino",
            type=int,
            default=8,
            help="Máximo de hoteles a cargar por destino (default 8)",
        )
        parser.add_argument(
            "--max-photos",
            type=int,
            default=3,
            help="Máximo de fotos a descargar por hotel (default 3)",
        )
        parser.add_argument("--dry-run", action="store_true", help="Simular sin guardar")

    def handle(self, *args, **options):
        """handle."""
        api_key = getattr(settings, "GOOGLE_PLACES_API_KEY", "")
        if not api_key:
            self.stdout.write(self.style.ERROR("❌ GOOGLE_PLACES_API_KEY no está configurada"))
            return

        destinos = [options["destino"]] if options.get("destino") else DESTINOS_VENEZUELA
        max_por_destino = options.get("max_por_destino", 8)
        max_photos = options.get("max_photos", 3)
        dry_run = options.get("dry_run", False)

        self.stdout.write(
            self.style.SUCCESS(
                f"🚀 Iniciando carga masiva de hoteles para {len(destinos)} destinos en Venezuela..."
            )
        )

        total_creados = 0
        total_actualizados = 0
        total_fotos = 0

        for idx, dest in enumerate(destinos, 1):
            self.stdout.write(f"\n📍 [{idx}/{len(destinos)}] Buscando alojamientos en: {dest}")

            search_queries = [
                f"hoteles y posadas en {dest}, Venezuela",
            ]

            for query in search_queries:
                try:
                    search_url = "https://places.googleapis.com/v1/places:searchText"
                    headers = {
                        "Content-Type": "application/json",
                        "X-Goog-Api-Key": api_key,
                        "X-Goog-FieldMask": (
                            "places.id,places.displayName,places.formattedAddress,"
                            "places.location,places.rating,places.photos,places.editorialSummary,"
                            "places.types"
                        ),
                    }
                    body = {
                        "textQuery": query,
                        "pageSize": max_por_destino,
                    }

                    resp = requests.post(search_url, headers=headers, json=body, timeout=15)
                    if resp.status_code != 200:
                        self.stdout.write(
                            self.style.WARNING(
                                f"  ⚠️ Error en la búsqueda HTTP {resp.status_code}: {resp.text[:100]}"
                            )
                        )
                        continue

                    data = resp.json()
                    places = data.get("places", [])

                    if not places:
                        self.stdout.write(self.style.NOTICE(f"  Sin resultados para: {query}"))
                        continue

                    self.stdout.write(f"  Coincidencias encontradas: {len(places)}")

                    for place in places:
                        nombre = place.get("displayName", {}).get("text", "").strip()
                        if not nombre:
                            continue

                        direccion = place.get("formattedAddress", "")
                        rating = place.get("rating", 0)
                        photos = place.get("photos", [])

                        # Coordenadas
                        loc = place.get("location", {})
                        coords = (
                            f"{loc.get('latitude', '')},{loc.get('longitude', '')}" if loc else ""
                        )

                        # Categoría estimada
                        categoria = 3
                        types = place.get("types", [])
                        if "resort_hotel" in types or rating >= 4.6:
                            categoria = 4
                        elif (
                            "guest_house" in types
                            or "bed_and_breakfast" in types
                            or "posada" in nombre.lower()
                        ):
                            categoria = 1
                        elif rating >= 4.0:
                            categoria = 3

                        # Descripción corta/larga
                        summary = (
                            place.get("editorialSummary", {}).get("text", "")
                            or f"Alojamiento {nombre} ubicado en {dest}, Venezuela."
                        )

                        self.stdout.write(f"   🏨 {nombre} (Rating: {rating}⭐)")

                        if not dry_run:
                            # Buscar o crear hotel
                            hotel = HotelTarifario.all_objects.filter(
                                nombre__iexact=nombre, destino__iexact=dest
                            ).first()

                            creado = False
                            if not hotel:
                                hotel = HotelTarifario.objects.create(
                                    nombre=nombre,
                                    destino=dest,
                                    direccion=direccion[:500],
                                    coordenadas_mapa=coords,
                                    descripcion_corta=summary[:250],
                                    descripcion_larga=summary,
                                    categoria=categoria,
                                    activo=True,
                                )
                                creado = True
                                total_creados += 1
                            else:
                                if not hotel.direccion and direccion:
                                    hotel.direccion = direccion[:500]
                                if not hotel.coordenadas_mapa and coords:
                                    hotel.coordenadas_mapa = coords
                                hotel.save()
                                total_actualizados += 1

                            # Descargar fotos si no tiene portada
                            if photos and (creado or not hotel.imagen_principal):
                                num_photos = min(max_photos, len(photos))
                                self.stdout.write(f"      Descargando {num_photos} foto(s)...")

                                for i, photo in enumerate(photos[:num_photos]):
                                    photo_name = photo.get("name", "")
                                    if not photo_name:
                                        continue

                                    photo_url = (
                                        f"https://places.googleapis.com/v1/{photo_name}/media"
                                        f"?maxWidthPx=1200&key={api_key}"
                                    )
                                    try:
                                        p_resp = requests.get(
                                            photo_url, timeout=12, allow_redirects=True
                                        )
                                        if p_resp.status_code == 200 and len(p_resp.content) > 1000:
                                            img_filename = (
                                                f"{slugify(hotel.nombre)}-{slugify(dest)}-{i}.jpg"
                                            )
                                            if i == 0 and not hotel.imagen_principal:
                                                hotel.imagen_principal.save(
                                                    img_filename,
                                                    ContentFile(p_resp.content),
                                                    save=True,
                                                )
                                                total_fotos += 1
                                            else:
                                                ImagenHotel.objects.create(
                                                    hotel=hotel,
                                                    titulo=f"Foto {i + 1} Google",
                                                    tipo="GENERAL",
                                                    es_portada=(i == 0),
                                                ).imagen.save(
                                                    img_filename,
                                                    ContentFile(p_resp.content),
                                                    save=True,
                                                )
                                                total_fotos += 1
                                    except Exception as img_err:
                                        logger.warning(f"Error descargando foto: {img_err}")
                        else:
                            self.stdout.write(f"      [DRY-RUN] Simulado {nombre}")

                        time.sleep(0.1)

                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"  ❌ Error procesando destino {dest}: {e}")
                    )

            time.sleep(0.2)

        self.stdout.write(
            self.style.SUCCESS(
                f"\n🎉 Carga Masiva Finalizada con éxito!\n"
                f"   - Hoteles Nuevos Creados: {total_creados}\n"
                f"   - Hoteles Actualizados: {total_actualizados}\n"
                f"   - Fotos Descargadas: {total_fotos}\n"
            )
        )
