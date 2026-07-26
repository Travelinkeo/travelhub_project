"""
Comando para enriquecer hoteles con fotos de Google Places API.
Busca el hotel por nombre + destino, descarga fotos y las guarda en el modelo.

Uso:
  python manage.py enriquecer_hoteles_fotos                    # Todos los hoteles sin foto
  python manage.py enriquecer_hoteles_fotos --agencia-id=2     # Solo de una agencia
  python manage.py enriquecer_hoteles_fotos --hotel-id=1       # Solo un hotel especifico
  python manage.py enriquecer_hoteles_fotos --dry-run           # Simular sin guardar
"""

import time

import requests
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from apps.bookings.models import HotelTarifario, ImagenHotel


class Command(BaseCommand):
    """Command."""

    help = "Enriquece hoteles con fotos de Google Places API"

    def add_arguments(self, parser):
        """add_arguments."""
        parser.add_argument("--agencia-id", type=int, default=None)
        parser.add_argument("--hotel-id", type=int, default=None)
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument(
            "--force", action="store_true", help="Forzar descarga y reemplazar fotos existentes"
        )
        parser.add_argument(
            "--max-photos", type=int, default=3, help="Max fotos por hotel (default 3)"
        )
        parser.add_argument(
            "--delay", type=float, default=0.2, help="Delay entre requests (default 0.2s)"
        )

    def handle(self, *args, **options):
        """handle."""
        api_key = getattr(settings, "GOOGLE_PLACES_API_KEY", "")
        if not api_key:
            self.stdout.write(self.style.ERROR("GOOGLE_PLACES_API_KEY no configurada"))
            return

        # Filtrar hoteles (usar all_objects para bypass tenant filter)
        if options.get("force"):
            qs = HotelTarifario.all_objects.filter(activo=True)
        else:
            qs = HotelTarifario.all_objects.filter(
                activo=True,
                imagen_principal="",
            )
        if options.get("agencia_id"):
            qs = qs.filter(agencia_id=options["agencia_id"])
        if options.get("hotel_id"):
            qs = qs.filter(id=options["hotel_id"])

        hotels = list(qs)
        self.stdout.write(f"Hoteles a enriquecer: {len(hotels)}")

        success = 0
        errors = 0
        delay = options.get("delay", 0.2)

        for hotel in hotels:
            query = f"{hotel.nombre} hotel {hotel.destino}"
            self.stdout.write(f"\n  Buscando: {query}")

            try:
                # Step 1: Find Place (Places API New - v1)
                search_url = "https://places.googleapis.com/v1/places:searchText"
                headers = {
                    "Content-Type": "application/json",
                    "X-Goog-Api-Key": api_key,
                    "X-Goog-FieldMask": "places.id,places.displayName,places.photos,places.formattedAddress,places.rating",
                }
                resp = requests.post(
                    search_url, headers=headers, json={"textQuery": query}, timeout=15
                )
                resp.raise_for_status()
                data = resp.json()

                places = data.get("places", [])
                if not places:
                    self.stdout.write(self.style.WARNING("    No encontrado en Google Places"))
                    errors += 1
                    time.sleep(delay)
                    continue

                place = places[0]
                place_id = place.get("id", "")
                display_name = place.get("displayName", {}).get("text", "?")
                self.stdout.write(f"    Place ID: {place_id} | {display_name}")

                # Update hotel details from Google
                if not options.get("dry_run"):
                    if place.get("formattedAddress") and not hotel.direccion:
                        hotel.direccion = place["formattedAddress"][:500]
                        hotel.save(update_fields=["direccion"])

                    if options.get("force"):
                        # Borrar fotos viejas de la galería
                        ImagenHotel.objects.filter(hotel=hotel).delete()
                        # Vaciar imagen principal anterior para permitir descarga
                        if hotel.imagen_principal:
                            try:
                                hotel.imagen_principal.delete(save=False)
                            except Exception as e:
                                self.stdout.write(
                                    self.style.WARNING(
                                        f"      No se pudo borrar archivo físico: {e}"
                                    )
                                )
                            hotel.imagen_principal = ""
                            hotel.save(update_fields=["imagen_principal"])

                # Step 2: Get photos (Places API New)
                photos = place.get("photos", [])
                if not photos:
                    self.stdout.write("    Sin fotos disponibles")
                    errors += 1
                    time.sleep(delay)
                    continue

                max_photos = min(options.get("max_photos", 3), len(photos))
                self.stdout.write(f"    {len(photos)} fotos disponibles, descargando {max_photos}")

                for i, photo in enumerate(photos[:max_photos]):
                    photo_name = photo.get("name", "")
                    if not photo_name:
                        continue

                    photo_url = (
                        f"https://places.googleapis.com/v1/{photo_name}/media"
                        f"?maxWidthPx=1200&key={api_key}"
                    )
                    photo_resp = requests.get(photo_url, timeout=15, allow_redirects=True)
                    if photo_resp.status_code == 200 and len(photo_resp.content) > 1000:
                        if not options.get("dry_run"):
                            img_name = f"{hotel.slug}_place_{i}.jpg"

                            if i == 0 and not hotel.imagen_principal:
                                hotel.imagen_principal.save(
                                    img_name, ContentFile(photo_resp.content), save=True
                                )
                                self.stdout.write(f"    [OK] Portada guardada: {img_name}")
                            else:
                                img = ImagenHotel(
                                    hotel=hotel,
                                    titulo=f"Google Places #{i + 1}",
                                    tipo="GENERAL",
                                    es_portada=(i == 0),
                                )
                                img.imagen.save(
                                    img_name, ContentFile(photo_resp.content), save=True
                                )
                                self.stdout.write(f"    [OK] Foto galeria #{i + 1} guardada")
                        else:
                            self.stdout.write(
                                f"    [DRY] Foto {i + 1} ({len(photo_resp.content)} bytes)"
                            )
                    else:
                        self.stdout.write(f"    [WARN] Foto {i + 1}: HTTP {photo_resp.status_code}")

                success += 1

            except requests.RequestException as e:
                self.stdout.write(self.style.ERROR(f"    Error de red: {e}"))
                errors += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"    Error: {e}"))
                errors += 1

            time.sleep(delay)

        self.stdout.write(
            self.style.SUCCESS(
                f"\n=== ENRIQUECIMIENTO COMPLETADO ===\nExitosos: {success}\nErrores: {errors}"
            )
        )
