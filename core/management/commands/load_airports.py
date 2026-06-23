import csv
import io

import requests
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Descarga la base de datos de OurAirports e importa los aeropuertos comerciales en la base de datos local."

    def handle(self, *args, **options):
        from core.models import Aeropuerto

        url = "https://davidmegginson.github.io/ourairports-data/airports.csv"
        self.stdout.write(f"Descargando base de datos de aeropuertos desde: {url}...")

        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
        except Exception as e:
            self.stderr.write(f"Error descargando el archivo CSV: {e}")
            return

        self.stdout.write("Procesando datos CSV...")
        csv_file = io.StringIO(response.text)
        reader = csv.DictReader(csv_file)

        # Limpiar tabla anterior
        self.stdout.write("Limpiando registros previos de aeropuertos...")
        Aeropuerto.objects.all().delete()

        aeropuertos_a_crear = []
        contador = 0

        # Mapeo de aeropuertos principales sugeridos para marcar como es_principal
        PRINCIPALES_IATA = {
            "CCS",
            "PMV",
            "MAR",
            "BLA",
            "STD",
            "LFR",
            "MIA",
            "JFK",
            "MAD",
            "BOG",
            "PTY",
            "CDG",
            "LHR",
            "EZE",
            "GRU",
            "MEX",
            "CUN",
        }

        for row in reader:
            # Filtrar solo aeropuertos comerciales medianos y grandes que tengan código IATA válido (3 letras)
            iata = (row.get("iata_code") or "").strip().upper()
            airport_type = (row.get("type") or "").strip()

            if len(iata) == 3 and airport_type in ("medium_airport", "large_airport"):
                try:
                    lat = float(row.get("latitude_deg", 0.0))
                    lon = float(row.get("longitude_deg", 0.0))
                except (ValueError, TypeError):
                    lat = 0.0
                    lon = 0.0

                nombre = row.get("name") or "Aeropuerto sin nombre"
                ciudad = row.get("municipality") or row.get("iso_region") or "Desconocida"
                pais = row.get("iso_country") or "XX"

                aeropuerto = Aeropuerto(
                    codigo_iata=iata,
                    nombre=nombre,
                    ciudad=ciudad,
                    pais=pais,
                    pais_codigo=pais,
                    latitud=lat,
                    longitud=lon,
                    es_principal=(iata in PRINCIPALES_IATA),
                )

                aeropuertos_a_crear.append(aeropuerto)
                contador += 1

        self.stdout.write(
            f"Guardando {len(aeropuertos_a_crear)} aeropuertos comerciales en la base de datos..."
        )

        # Bulk create en lotes de 500 para evitar saturar la base de datos
        Aeropuerto.objects.bulk_create(aeropuertos_a_crear, batch_size=500, ignore_conflicts=True)

        self.stdout.write(
            self.style.SUCCESS(
                f"¡Base de datos de aeropuertos cargada exitosamente! Se importaron {contador} registros."
            )
        )
