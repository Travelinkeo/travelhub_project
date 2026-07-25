"""Comando para calentar el caché con datos frecuentes"""

from django.core.cache import cache
from django.core.management.base import BaseCommand

from apps.bookings.models import ProductoServicio
from apps.common.models import Aerolinea, Ciudad, Moneda, Pais


class Command(BaseCommand):
    """Comando de gestión personalizado."""
    help = "Calienta el caché con datos de catálogos frecuentes"

    def handle(self, *args, **options):
        """Método: handle."""
        self.stdout.write("Calentando caché...")

        CHUNK_SIZE = 1000

        # Países
        paises = list(Pais.objects.all().iterator(CHUNK_SIZE))
        cache.set("paises_list", paises, 3600)
        self.stdout.write(f"✅ Países: {len(paises)} registros")

        # Ciudades
        ciudades = list(Ciudad.objects.select_related("pais").all().iterator(CHUNK_SIZE))
        cache.set("ciudades_list:", ciudades, 1800)
        self.stdout.write(f"✅ Ciudades: {len(ciudades)} registros")

        # Monedas
        monedas = list(Moneda.objects.all().iterator(CHUNK_SIZE))
        cache.set("monedas_list", monedas, 3600)
        self.stdout.write(f"✅ Monedas: {len(monedas)} registros")

        # Aerolíneas
        aerolineas = list(Aerolinea.objects.filter(activa=True).iterator(CHUNK_SIZE))
        cache.set("aerolineas_list", aerolineas, 3600)
        self.stdout.write(f"✅ Aerolíneas: {len(aerolineas)} registros")

        # Productos/Servicios
        productos = list(ProductoServicio.objects.filter(activo=True).iterator(CHUNK_SIZE))
        cache.set("productos_list", productos, 1800)
        self.stdout.write(f"✅ Productos: {len(productos)} registros")

        self.stdout.write(self.style.SUCCESS("✅ Caché calentado exitosamente"))
