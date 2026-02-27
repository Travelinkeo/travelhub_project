from django.core.management.base import BaseCommand
from core.models.wiki import WikiArticulo
from django.utils.text import slugify

class Command(BaseCommand):
    help = 'Loads GDS Master Guides into Wiki Knowledge Base'

    def handle(self, *args, **kwargs):
        guides = [
            {
                'title': 'Guía Maestra AMADEUS (Comandos GDS)',
                'tags': ['AMADEUS', 'GDS', 'COMANDOS', 'MANUAL', 'RESERVA'],
                'content': """# Guía Maestra Amadeus GDS

## 1. Flujo de Reserva
### A. Disponibilidad (AN)
- **Neutral**: AN[Fecha][Org][Dst] (Ej: AN15OCTMIALON)
- **Aerolínea**: AN[Fecha][Org][Dst]/A[Airline]

### B. Venta (SS)
- **Reservar**: SS[Cant][Clase][Línea] (Ej: SS1K1)
- **Directa**: SS LH463 K 15OCT MIAMUC NN1

### C. Nombres (NM)
- **Pax**: NM1[Apellido]/[Nombre] [Título]
- **Niño**: NM1[Apellido]/[Nombre](CHD)
- **Infante**: NM1[Apellido]/[Nombre](INF...)

### D. Contacto (AP)
- **Móvil**: AP [Ciudad]-[Num]-M
- **Email**: APE-[Email]

### E. Tiempo Límite (TK)
- **Set**: TKTL[Fecha]
- **Ticketed**: TKOK

### F. Fin (E)
- **Grabar**: ET
- **Grabar y Recuperar**: ER
- **Ignorar**: IG

## 2. Tarifación (F)
- **Tarifar**: FXP
- **Informativo**: FXX
- **Mejor Precio**: FXB

## 3. Servicios Especiales (DOCS/APIS)
- **Pasaporte**: SR DOCS [Airline] HK1-P-[Pais]-[Num]-[Nac]-[Nacim]-[Gen]-[Venc]-[Last]-[First]
  - Ej: SR DOCS YY HK1-P-VEN-12345678-VEN-30JUN85-M-15JAN30-PEREZ-JUAN
- **Dirección (USA)**: SR DOCA ... HK1-R-USA-...
- **Visa**: SR DOCO ... HK1-...

## 4. Ancillarios
- **Hoteles**: HA[Ciudad][Fecha][Noches] -> HS[Línea]
- **Autos**: CA[Ciudad][Fecha]-[Fecha] -> CS[Línea]
"""
            },
            {
                'title': 'Guía Maestra SABRE (Comandos GDS)',
                'tags': ['SABRE', 'GDS', 'COMANDOS', 'MANUAL', '1', '0'],
                'content': """# Guía Maestra Sabre GDS

## 1. Flujo de Reserva
### A. Disponibilidad (1)
- **Neutral**: 1[Fecha][Org][Dst] (Ej: 115OCTMIALON)
- **Con Aerolinea**: 1[Fecha][Org][Dst]¥[Airline]

### B. Venta (0)
- **Reservar**: 0[Cant][Clase][Línea] (Ej: 01Y1)
- **Directa**: 0AA905Y15OCTMIALONNN1

### C. Nombres (-)
- **Pax**: -[Apellido]/[Nombre]
- **Múltiples**: -[Apellido]/[Nombre]/[Nombre2]
- **Infante**: -I/[Apellido]/[Nombre] o asociado

### D. Contacto (9)
- **Teléfono**: 9[Tel]-[Tipo] (Ej: 9305123-M)
- **Email**: PE¥[Email] o 3CTCE...

### E. Tiempo Límite (7)
- **Set**: 7TAW[Fecha]/
- **Firma**: 6[Iniciales]

### F. Fin (E)
- **Grabar**: E
- **Grabar y Recuperar**: ER
- **Ignorar**: I

## 2. Tarifación (WP)
- **Precio**: WP
- **Mejor Precio**: WPNC
- **Mejor + Reservar**: WPNCB
- **Guardar**: PQ

## 3. Servicios Especiales (3)
- **Pasaporte**: 3DOCS/P/[Pais]/[Num]/[Nac]/[Nacim]/[Gen]/[Venc]/[Last]/[First]
  - Ej: 3DOCS/P/VEN/12345678/VEN/30JUN85/M/15JAN30/PEREZ/JUAN
- **Dirección**: 3DOCA/R/USA/...
- **OSI**: 3OSI AA VIP

## 4. Ancillarios
- **Hoteles**: HOT[Ciudad]/... -> 0H[Línea]
- **Autos**: CAR[Ciudad]/... -> 0C[Línea]
"""
            },
            {
                'title': 'Guía Maestra KIU (Comandos GDS)',
                'tags': ['KIU', 'GDS', 'COMANDOS', 'MANUAL', 'CONVIASA', 'LASER'],
                'content': """# Guía Maestra KIU GDS (Sistema Híbrido)

## 1. Flujo de Reserva
### A. Disponibilidad (1)
- **Neutral**: 1[Fecha][Org][Dst] (Ej: 122AUGCCSSDQ)
- **Igual que Sabre**

### B. Venta (0)
- **Reservar**: 0[Cant][Clase][Línea] (Ej: 01W1)

### C. Nombres (-)
- **Pax**: -[Apellido]/[Nombre]
- **Con ID**: -[Apellido]/[Nombre].ID12345 (A veces usado, preferible SSR)

### D. Contacto (9)
- **Teléfono**: 9[Ciudad][Tel]-[Texto]

### E. Tiempo Límite (8)
- **Set**: 8[Status][Hora]/[Fecha] (Ej: 8X2359/21JUL)
- **Firma**: 6[Nombre]

### F. Fin (E)
- **Grabar**: E
- **Recuperar**: ER
- **Cambiar Área**: ø1, ø2

## 2. Tarifación (WS)
- **Precio Adulto**: WS
- **Precio Niño**: WS*PCHD
- **Display Tarifa**: FQ

## 3. Servicios Especiales (3)
- **Pasaporte**: 3DOCS/[Tipo]/[Pais]/[Num]... (Igual formato IATA)
- **FOID**: 3FOID/[Airline] HK/[Tipo][Num]-1.1 (Crucial en KIU)
"""
            }
        ]

        for guia in guides:
            articulo, created = WikiArticulo.objects.update_or_create(
                slug=slugify(guia['title']),
                defaults={
                    'titulo': guia['title'],
                    'contenido': guia['content'],
                    'tags': guia['tags'],
                    'categoria': 'GENERAL', # Podríamos agregar GDS si modificamos el modelo, pero GENERAL funciona
                    'activo': True
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Creado: {articulo.titulo}'))
            else:
                self.stdout.write(self.style.WARNING(f'Actualizado: {articulo.titulo}'))
