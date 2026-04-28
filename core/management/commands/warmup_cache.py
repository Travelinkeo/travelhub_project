"""Comando para calentar el caché con datos frecuentes"""
from django.core.management.base import BaseCommand
from django.core.cache import cache
from core.models_catalogos import Pais, Ciudad, Moneda, Aerolinea, ProductoServicio


class Command(BaseCommand):
    help = 'Calienta el caché con datos de catálogos frecuentes'
    
    def handle(self, *args, **options):
        self.stdout.write('Calentando caché...')
        
        # Países
        paises = list(Pais.objects.all().values())
        cache.set('paises_list', paises, 3600)
        self.stdout.write(f'✅ Países: {len(paises)} registros')
        
        # Ciudades
        ciudades = list(Ciudad.objects.select_related('pais').all().values())
        cache.set('ciudades_list:', ciudades, 1800)
        self.stdout.write(f'✅ Ciudades: {len(ciudades)} registros')
        
        # Monedas
        monedas = list(Moneda.objects.all().values())
        cache.set('monedas_list', monedas, 3600)
        self.stdout.write(f'✅ Monedas: {len(monedas)} registros')
        
        # Aerolíneas
        aerolineas = list(Aerolinea.objects.filter(activa=True).values())
        cache.set('aerolineas_list', aerolineas, 3600)
        self.stdout.write(f'✅ Aerolíneas: {len(aerolineas)} registros')
        
        # Productos/Servicios
        productos = list(ProductoServicio.objects.filter(activo=True).values())
        cache.set('productos_list', productos, 1800)
        self.stdout.write(f'✅ Productos: {len(productos)} registros')
        
        self.stdout.write(self.style.SUCCESS('✅ Caché calentado exitosamente'))
