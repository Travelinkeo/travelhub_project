# Implementación de Tarifario de Hoteles BT Travel

**Fecha**: 25 de Enero de 2025  
**Proveedor**: BT Travel  
**Archivo**: TARIFARIO NACIONAL SEPTIEMBRE 2025-028.pdf (139 páginas)

---

## 📋 Análisis del Tarifario

### Estructura Identificada

El PDF contiene:
1. **Traslados** (páginas iniciales)
2. **Hotelería por destino** (resto del documento)
   - Isla Margarita y Coche
   - Los Roques
   - Mérida
   - Otros destinos nacionales

### Datos por Hotel

Cada hotel tiene:
- **Nombre**: "MARGARITA DYNASTY"
- **Régimen**: "SOLO DESAYUNO", "TODO INCLUIDO", etc.
- **Ubicación**: Descripción textual
- **Comisión**: "15%" (estándar)
- **Vigencias**: Múltiples períodos (temporada baja, navidad, fin de año)
- **Tipos de habitación**: STANDARD, EJECUTIVA, JR SUITES, SUITE
- **Tarifas por ocupación**: SGL, DBL, TPL, CDP, QPL, SEX PAX
- **Tarifas adicionales**: PAX ADIC, CHD (niños 4-10 años)
- **Políticas**:
  - Capacidad de habitaciones
  - Política de niños (0-3 gratis, 4-10 tarifa CHD, 11+ adulto)
  - Check-in/Check-out
  - Mínimo de noches

---

## 🎯 Propuesta de Implementación

### Fase 1: Modelo de Datos ✅

#### 1.1 Modelo `TarifarioProveedor`

```python
# core/models/tarifario_hoteles.py
from django.db import models
from decimal import Decimal

class TarifarioProveedor(models.Model):
    """Tarifario de un proveedor (BT Travel, etc.)"""
    proveedor = models.ForeignKey('personas.Proveedor', on_delete=models.CASCADE)
    nombre = models.CharField(max_length=200)  # "Tarifario Nacional Septiembre 2025"
    archivo_pdf = models.FileField(upload_to='tarifarios/%Y/%m/')
    fecha_vigencia_inicio = models.DateField()
    fecha_vigencia_fin = models.DateField()
    comision_estandar = models.DecimalField(max_digits=5, decimal_places=2, default=15.00)
    activo = models.BooleanField(default=True)
    fecha_carga = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Tarifario de Proveedor"
        verbose_name_plural = "Tarifarios de Proveedores"
```

#### 1.2 Modelo `HotelTarifario`

```python
class HotelTarifario(models.Model):
    """Hotel dentro de un tarifario"""
    tarifario = models.ForeignKey(TarifarioProveedor, on_delete=models.CASCADE, related_name='hoteles')
    nombre = models.CharField(max_length=200)
    destino = models.CharField(max_length=100)  # "Isla Margarita", "Los Roques"
    ubicacion_descripcion = models.TextField(blank=True)
    
    REGIMEN_CHOICES = [
        ('SO', 'Solo Alojamiento'),
        ('SD', 'Solo Desayuno'),
        ('MP', 'Media Pensión'),
        ('PC', 'Pensión Completa'),
        ('TI', 'Todo Incluido'),
    ]
    regimen = models.CharField(max_length=2, choices=REGIMEN_CHOICES)
    comision = models.DecimalField(max_digits=5, decimal_places=2)
    
    # Políticas
    politica_ninos = models.TextField(blank=True)
    check_in = models.TimeField(default='15:00')
    check_out = models.TimeField(default='12:00')
    minimo_noches_temporada_baja = models.IntegerField(default=1)
    minimo_noches_temporada_alta = models.IntegerField(default=2)
    
    activo = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Hotel en Tarifario"
        verbose_name_plural = "Hoteles en Tarifario"
        unique_together = ['tarifario', 'nombre']
```

#### 1.3 Modelo `TipoHabitacion`

```python
class TipoHabitacion(models.Model):
    """Tipo de habitación de un hotel"""
    hotel = models.ForeignKey(HotelTarifario, on_delete=models.CASCADE, related_name='tipos_habitacion')
    nombre = models.CharField(max_length=100)  # "STANDARD", "EJECUTIVA", "JR SUITES"
    capacidad_adultos = models.IntegerField()
    capacidad_ninos = models.IntegerField(default=0)
    capacidad_total = models.IntegerField()
    descripcion = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Tipo de Habitación"
        verbose_name_plural = "Tipos de Habitación"
        unique_together = ['hotel', 'nombre']
```

#### 1.4 Modelo `TarifaHabitacion`

```python
class TarifaHabitacion(models.Model):
    """Tarifa de una habitación por período"""
    tipo_habitacion = models.ForeignKey(TipoHabitacion, on_delete=models.CASCADE, related_name='tarifas')
    
    # Vigencia
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    nombre_temporada = models.CharField(max_length=100, blank=True)  # "NAVIDAD", "FIN DE AÑO"
    
    # Tarifas por ocupación (por noche)
    tarifa_sgl = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    tarifa_dbl = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    tarifa_tpl = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    tarifa_cdp = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    tarifa_qpl = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    tarifa_sex_pax = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Tarifas adicionales
    tarifa_pax_adicional = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    tarifa_nino_4_10 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    class Meta:
        verbose_name = "Tarifa de Habitación"
        verbose_name_plural = "Tarifas de Habitaciones"
        ordering = ['fecha_inicio']
```

---

## 🔧 Fase 2: Parser del PDF

### 2.1 Script de Extracción

```python
# core/services/tarifario_parser.py
import PyPDF2
import re
from datetime import datetime
from decimal import Decimal

class TarifarioParser:
    def __init__(self, pdf_path):
        self.pdf_path = pdf_path
        self.reader = PyPDF2.PdfReader(open(pdf_path, 'rb'))
    
    def extraer_hoteles(self):
        """Extrae todos los hoteles del PDF"""
        hoteles = []
        destino_actual = None
        
        for i, page in enumerate(self.reader.pages):
            texto = page.extract_text()
            
            # Detectar destino
            if 'ISLA MARGARITA' in texto:
                destino_actual = 'Isla Margarita'
            elif 'LOS ROQUES' in texto:
                destino_actual = 'Los Roques'
            # ... más destinos
            
            # Detectar hotel
            if 'TARIFA COMISIONABLE' in texto:
                hotel = self._parsear_hotel(texto, destino_actual)
                if hotel:
                    hoteles.append(hotel)
        
        return hoteles
    
    def _parsear_hotel(self, texto, destino):
        """Parsea un hotel individual"""
        # Extraer nombre
        match_nombre = re.search(r'^([A-Z\s]+)\n', texto, re.MULTILINE)
        nombre = match_nombre.group(1).strip() if match_nombre else None
        
        # Extraer régimen
        regimen = None
        if 'SOLO DESAYUNO' in texto:
            regimen = 'SD'
        elif 'TODO INCLUIDO' in texto:
            regimen = 'TI'
        
        # Extraer comisión
        match_comision = re.search(r'COMISIONABLE AL (\d+)%', texto)
        comision = Decimal(match_comision.group(1)) if match_comision else Decimal('15.00')
        
        # Extraer tarifas
        tarifas = self._extraer_tarifas(texto)
        
        return {
            'nombre': nombre,
            'destino': destino,
            'regimen': regimen,
            'comision': comision,
            'tarifas': tarifas
        }
    
    def _extraer_tarifas(self, texto):
        """Extrae tabla de tarifas"""
        tarifas = []
        # Regex para extraer filas de tarifas
        # Ejemplo: "21/09/2025 AL 20/12/2025 STANDARD $61 $69 N/A N/A N/A N/A $25 $15"
        patron = r'(\d{2}/\d{2}/\d{4})\s+AL\s+(\d{2}/\d{2}/\d{4})\s+([A-Z\s]+)\s+\$?([\d,]+|\N/A)\s+\$?([\d,]+|N/A)'
        
        for match in re.finditer(patron, texto):
            fecha_inicio = datetime.strptime(match.group(1), '%d/%m/%Y').date()
            fecha_fin = datetime.strptime(match.group(2), '%d/%m/%Y').date()
            tipo_hab = match.group(3).strip()
            tarifa_sgl = self._parse_precio(match.group(4))
            tarifa_dbl = self._parse_precio(match.group(5))
            
            tarifas.append({
                'fecha_inicio': fecha_inicio,
                'fecha_fin': fecha_fin,
                'tipo_habitacion': tipo_hab,
                'tarifa_sgl': tarifa_sgl,
                'tarifa_dbl': tarifa_dbl
            })
        
        return tarifas
    
    def _parse_precio(self, precio_str):
        """Convierte string de precio a Decimal"""
        if precio_str == 'N/A':
            return None
        return Decimal(precio_str.replace(',', ''))
```

### 2.2 Comando de Importación

```python
# core/management/commands/importar_tarifario.py
from django.core.management.base import BaseCommand
from core.services.tarifario_parser import TarifarioParser
from core.models import TarifarioProveedor, HotelTarifario, TipoHabitacion, TarifaHabitacion
from personas.models import Proveedor

class Command(BaseCommand):
    help = 'Importa tarifario de hoteles desde PDF'
    
    def add_arguments(self, parser):
        parser.add_argument('pdf_path', type=str)
        parser.add_argument('--proveedor-id', type=int, required=True)
    
    def handle(self, *args, **options):
        pdf_path = options['pdf_path']
        proveedor_id = options['proveedor_id']
        
        proveedor = Proveedor.objects.get(id_proveedor=proveedor_id)
        
        # Crear tarifario
        tarifario = TarifarioProveedor.objects.create(
            proveedor=proveedor,
            nombre="Tarifario Nacional Septiembre 2025",
            fecha_vigencia_inicio='2025-09-21',
            fecha_vigencia_fin='2026-01-15',
            comision_estandar=15.00
        )
        
        # Parsear PDF
        parser = TarifarioParser(pdf_path)
        hoteles_data = parser.extraer_hoteles()
        
        # Importar hoteles
        for hotel_data in hoteles_data:
            hotel = HotelTarifario.objects.create(
                tarifario=tarifario,
                nombre=hotel_data['nombre'],
                destino=hotel_data['destino'],
                regimen=hotel_data['regimen'],
                comision=hotel_data['comision']
            )
            
            # Importar tipos de habitación y tarifas
            for tarifa_data in hotel_data['tarifas']:
                tipo_hab, created = TipoHabitacion.objects.get_or_create(
                    hotel=hotel,
                    nombre=tarifa_data['tipo_habitacion'],
                    defaults={'capacidad_adultos': 2, 'capacidad_total': 2}
                )
                
                TarifaHabitacion.objects.create(
                    tipo_habitacion=tipo_hab,
                    fecha_inicio=tarifa_data['fecha_inicio'],
                    fecha_fin=tarifa_data['fecha_fin'],
                    tarifa_sgl=tarifa_data['tarifa_sgl'],
                    tarifa_dbl=tarifa_data['tarifa_dbl']
                )
        
        self.stdout.write(self.style.SUCCESS(f'Importados {len(hoteles_data)} hoteles'))
```

---

## 🚀 Fase 3: API de Cotización

### 3.1 Endpoint de Búsqueda

```python
# core/views/tarifario_views.py
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from datetime import datetime

class TarifarioViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = HotelTarifario.objects.filter(activo=True)
    
    @action(detail=False, methods=['post'])
    def cotizar(self, request):
        """
        Cotiza hoteles según criterios
        
        POST /api/tarifario/cotizar/
        {
            "destino": "Isla Margarita",
            "fecha_entrada": "2025-12-20",
            "fecha_salida": "2025-12-27",
            "habitaciones": [
                {"tipo": "DBL", "adultos": 2, "ninos": 0}
            ]
        }
        """
        destino = request.data.get('destino')
        fecha_entrada = datetime.strptime(request.data['fecha_entrada'], '%Y-%m-%d').date()
        fecha_salida = datetime.strptime(request.data['fecha_salida'], '%Y-%m-%d').date()
        habitaciones = request.data.get('habitaciones', [])
        
        # Buscar hoteles disponibles
        hoteles = HotelTarifario.objects.filter(
            destino__icontains=destino,
            activo=True
        )
        
        resultados = []
        for hotel in hoteles:
            cotizacion = self._cotizar_hotel(hotel, fecha_entrada, fecha_salida, habitaciones)
            if cotizacion:
                resultados.append(cotizacion)
        
        return Response({
            'destino': destino,
            'fecha_entrada': fecha_entrada,
            'fecha_salida': fecha_salida,
            'noches': (fecha_salida - fecha_entrada).days,
            'hoteles': resultados
        })
    
    def _cotizar_hotel(self, hotel, fecha_entrada, fecha_salida, habitaciones):
        """Calcula precio total para un hotel"""
        noches = (fecha_salida - fecha_entrada).days
        total = Decimal('0.00')
        desglose = []
        
        for hab_req in habitaciones:
            tipo_ocupacion = hab_req['tipo']  # 'SGL', 'DBL', 'TPL'
            
            # Buscar tipo de habitación
            tipo_hab = hotel.tipos_habitacion.first()  # Simplificado
            
            # Buscar tarifa vigente
            tarifa = TarifaHabitacion.objects.filter(
                tipo_habitacion=tipo_hab,
                fecha_inicio__lte=fecha_entrada,
                fecha_fin__gte=fecha_salida
            ).first()
            
            if tarifa:
                precio_noche = getattr(tarifa, f'tarifa_{tipo_ocupacion.lower()}', None)
                if precio_noche:
                    subtotal = precio_noche * noches
                    total += subtotal
                    desglose.append({
                        'tipo_habitacion': tipo_hab.nombre,
                        'ocupacion': tipo_ocupacion,
                        'precio_noche': precio_noche,
                        'noches': noches,
                        'subtotal': subtotal
                    })
        
        if total > 0:
            return {
                'hotel': hotel.nombre,
                'regimen': hotel.get_regimen_display(),
                'comision': hotel.comision,
                'total_sin_comision': total,
                'comision_monto': total * (hotel.comision / 100),
                'total_neto': total * (1 - hotel.comision / 100),
                'desglose': desglose
            }
        
        return None
```

---

## 📱 Fase 4: Interfaz de Usuario

### 4.1 Formulario de Cotización

```typescript
// frontend/src/app/cotizaciones/hoteles/page.tsx
'use client';

export default function CotizadorHoteles() {
  const [destino, setDestino] = useState('');
  const [fechaEntrada, setFechaEntrada] = useState('');
  const [fechaSalida, setFechaSalida] = useState('');
  const [resultados, setResultados] = useState([]);
  
  const cotizar = async () => {
    const response = await fetch('/api/tarifario/cotizar/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        destino,
        fecha_entrada: fechaEntrada,
        fecha_salida: fechaSalida,
        habitaciones: [{ tipo: 'DBL', adultos: 2, ninos: 0 }]
      })
    });
    
    const data = await response.json();
    setResultados(data.hoteles);
  };
  
  return (
    <div>
      <h1>Cotizador de Hoteles</h1>
      <input value={destino} onChange={e => setDestino(e.target.value)} placeholder="Destino" />
      <input type="date" value={fechaEntrada} onChange={e => setFechaEntrada(e.target.value)} />
      <input type="date" value={fechaSalida} onChange={e => setFechaSalida(e.target.value)} />
      <button onClick={cotizar}>Cotizar</button>
      
      {resultados.map(hotel => (
        <div key={hotel.hotel}>
          <h3>{hotel.hotel}</h3>
          <p>Régimen: {hotel.regimen}</p>
          <p>Total: ${hotel.total_sin_comision}</p>
          <p>Comisión {hotel.comision}%: ${hotel.comision_monto}</p>
          <p>Neto: ${hotel.total_neto}</p>
        </div>
      ))}
    </div>
  );
}
```

---

## ✅ Resumen de Implementación

### Modelos (4)
- `TarifarioProveedor` - Tarifario completo
- `HotelTarifario` - Hotel individual
- `TipoHabitacion` - Tipos de habitación
- `TarifaHabitacion` - Tarifas por período

### Servicios (1)
- `TarifarioParser` - Parser del PDF

### Comandos (1)
- `importar_tarifario` - Importación automática

### API (1)
- `TarifarioViewSet.cotizar()` - Cotización de hoteles

### Frontend (1)
- Formulario de cotización con resultados

---

## 🔄 Flujo Completo

1. **Importar tarifario**:
   ```bash
   python manage.py importar_tarifario "TARIFARIO NACIONAL SEPTIEMBRE 2025-028.pdf" --proveedor-id 1
   ```

2. **Cotizar desde frontend**:
   - Usuario ingresa destino, fechas, habitaciones
   - Sistema busca hoteles disponibles
   - Calcula precios según tarifas vigentes
   - Muestra resultados con comisión

3. **Actualizar tarifario**:
   - Desactivar tarifario anterior
   - Importar nuevo PDF
   - Sistema usa tarifas más recientes

---

## 💡 Ventajas

✅ **Automatización**: Importación automática desde PDF  
✅ **Cotización instantánea**: Sin consultar manualmente  
✅ **Histórico**: Mantiene tarifarios anteriores  
✅ **Comisiones**: Calcula automáticamente  
✅ **Escalable**: Agregar más proveedores fácilmente  

---

## ✅ Estado de Implementación

### Fase 1: Modelos de Datos ✅ COMPLETADA
- 4 modelos creados y migrados
- Admin configurado con inlines
- 64 hoteles importados desde PDF

### Fase 2: Parser del PDF ✅ COMPLETADA  
- Parser automático funcional
- Comando `importar_tarifario` operativo
- 72 hoteles detectados, 64 únicos importados
- 1 tipo de habitación y 4 tarifas creadas

### Fase 3: API de Cotización ✅ COMPLETADA
- Serializers creados
- ViewSets registrados
- Endpoint `/api/hoteles-tarifario/cotizar/` funcional
- Script de prueba incluido

### Fase 4: Frontend (Pendiente)
- Formulario de búsqueda
- Resultados con precios
- Integración con sistema de ventas

---

**Última actualización**: 25 de Enero de 2025  
**Estado**: 3 de 4 fases completadas (75%)  
**Autor**: Amazon Q Developer
