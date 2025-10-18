#!/usr/bin/env python
"""
Script para actualizar el catálogo de aerolíneas con las aerolíneas de KIU
"""
import os
import sys
import django

# Configurar Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.models_catalogos import Aerolinea

def main():
    print("=== Actualizando catálogo de aerolíneas KIU ===\n")
    
    # 1. Desactivar aerolíneas internacionales con códigos conflictivos
    print("1. Desactivando aerolíneas internacionales con códigos conflictivos...")
    conflictos = Aerolinea.objects.filter(codigo_iata__in=['CV', 'ES', 'O3', 'RU'])
    for aero in conflictos:
        print(f"   - Desactivando: {aero.codigo_iata} - {aero.nombre}")
    conflictos.update(activa=False)
    
    # 2. Crear/actualizar aerolíneas de KIU
    print("\n2. Creando/actualizando aerolíneas de KIU...")
    
    aerolineas_kiu = [
        ('5R', 'Rutaca'),
        ('7N', 'PAWA Dominicana'),
        ('7P', 'Air Panama'),
        ('9R', 'Satena'),
        ('9V', 'Avior Airlines'),
        ('A6', 'Pegaso Travel'),
        ('C3', 'CargoThree'),
        ('CV', 'Aerocaribe'),
        ('CW', 'Aeropostal Alas de Venezuela'),
        ('DO', 'Sky High'),
        ('E4', 'Estelar Latinoamerica'),
        ('ES', 'Estelar'),
        ('G0', 'Alianza Glancelot'),
        ('G6', 'Global Air'),
        ('GI', 'Fly The World'),
        ('L5', 'Red Air'),
        ('NU', 'Mundo Airways'),
        ('O3', 'SASCA Airlines'),
        ('PU', 'Plus Ultra'),
        ('QL', 'Laser Airlines'),
        ('RU', 'Global'),
        ('T5', 'Turpial'),
        ('T7', 'Sky Atlantic Travel'),
        ('T9', 'Turpial Airlines'),
        ('V0', 'Conviasa'),
        ('WW', 'Rutas Aereas de Venezuela'),
    ]
    
    for codigo, nombre in aerolineas_kiu:
        aero, created = Aerolinea.objects.update_or_create(
            codigo_iata=codigo,
            defaults={'nombre': nombre, 'activa': True}
        )
        if created:
            print(f"   [OK] Creada: {codigo} - {nombre}")
        else:
            print(f"   [OK] Actualizada: {codigo} - {nombre}")
    
    print("\n=== Proceso completado ===")
    print(f"Total de aerolíneas activas: {Aerolinea.objects.filter(activa=True).count()}")

if __name__ == '__main__':
    main()
