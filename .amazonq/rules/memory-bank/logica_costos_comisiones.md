# Lógica de Costos y Comisiones - TravelHub

**Fecha**: 24 de Enero de 2025  
**Estado**: Documentación completa

---

## 🎫 BOLETOS AÉREOS

### Componentes de Costo

```
COSTO TOTAL AL CLIENTE =
  Precio Boleto (tarifa neta)
  + Fee Proveedor/Consolidador
  + Fee Agencia
  + IGTF 3% (sobre todo lo anterior)
  - Comisión Proveedor (si aplica)
```

### Campos en ItemVenta / SegmentoVuelo

```python
# Costos
costo_neto_proveedor          # Precio del boleto (tarifa neta)
fee_proveedor                 # Fee que cobra el proveedor
comision_agencia_monto        # Comisión que paga el proveedor (si aplica)
fee_agencia_interno           # Fee que cobra la agencia al cliente

# Cálculo
precio_unitario_venta = (
    costo_neto_proveedor 
    + fee_proveedor 
    + fee_agencia_interno
) * 1.03  # IGTF 3%

# Pago al proveedor
pago_proveedor = (
    costo_neto_proveedor 
    + fee_proveedor
) - comision_agencia_monto

# Margen agencia
margen = comision_agencia_monto + fee_agencia_interno
```

### Ejemplo Práctico

**Boleto CCS-MIA**:
- Tarifa neta: $500
- Fee proveedor: $50
- Comisión proveedor: 5% = $25
- Fee agencia: $100
- IGTF 3%: ($500 + $50 + $100) × 0.03 = $19.50

**Resultado**:
- Cliente paga: $669.50
- Agencia paga a proveedor: $525 ($550 - $25 comisión)
- Margen agencia: $125 ($25 comisión + $100 fee)

### Anulaciones

```python
# Campo adicional en SegmentoVuelo
fecha_anulacion = models.DateField(blank=True, null=True)
costo_anulacion = models.DecimalField(max_digits=10, decimal_places=2, 
                                     blank=True, null=True)
motivo_anulacion = models.CharField(max_length=200, blank=True)

# Lógica
if fecha_anulacion:
    # Mismo día o día siguiente
    dias_diferencia = (fecha_anulacion - fecha_emision).days
    if dias_diferencia <= 1:
        # Aplicar costo de anulación
        # Restar del margen de la venta
```

---

## 🏨 SERVICIOS TERRESTRES

Incluye: Hoteles, Traslados, Alquiler de Autos, Actividades, Seguros, etc.

### Tipos de Tarifa

#### 1. Comisionable (Mayoría)

```
COSTO AL CLIENTE =
  Tarifa Proveedor (incluye comisión)
  + Fee Agencia (opcional)
  + IGTF 3%

PAGO AL PROVEEDOR =
  Tarifa Proveedor - Comisión
```

**Campos**:
```python
# En AlojamientoReserva, AlquilerAutoReserva, etc.
tarifa_proveedor = models.DecimalField(...)  # Tarifa total del proveedor
es_comisionable = models.BooleanField(default=True)
porcentaje_comision = models.DecimalField(...)  # 2% a 20%
monto_comision = models.DecimalField(...)  # Calculado automáticamente
fee_agencia = models.DecimalField(blank=True, null=True)  # Fee adicional
```

**Ejemplo Hotel**:
- Tarifa proveedor: $300 (3 noches)
- Comisión: 10% = $30
- Fee agencia: $0 (opcional)
- IGTF 3%: $300 × 0.03 = $9

**Resultado**:
- Cliente paga: $309
- Agencia paga a proveedor: $270 ($300 - $30)
- Margen agencia: $30

#### 2. No Comisionable

```
COSTO AL CLIENTE =
  Tarifa Neta Proveedor
  + Fee Agencia (obligatorio para ganancia)
  + IGTF 3%

PAGO AL PROVEEDOR =
  Tarifa Neta (sin descuento)
```

**Ejemplo Traslado**:
- Tarifa neta: $50
- Comisión: 0%
- Fee agencia: $15 (necesario para ganancia)
- IGTF 3%: ($50 + $15) × 0.03 = $1.95

**Resultado**:
- Cliente paga: $66.95
- Agencia paga a proveedor: $50
- Margen agencia: $15

### Factura del Proveedor

El proveedor envía:
```
Factura/Nota:
  Tarifa Total: $300
  Comisión 10%: -$30
  ─────────────────
  A Pagar: $270
```

---

## 💰 MONEDAS Y PAGOS

### Diferenciación por Moneda

```python
# En PagoVenta
class MetodoPago(models.TextChoices):
    EFECTIVO = 'EFE', _('Efectivo')
    TARJETA = 'TAR', _('Tarjeta')
    TRANSFERENCIA = 'TRF', _('Transferencia')
    ZELLE = 'ZEL', _('Zelle')  # Divisas
    PAYPAL = 'PPL', _('PayPal')  # Divisas
    PAGO_MOVIL = 'PMO', _('Pago Móvil')  # Bolívares
    OTRO = 'OTR', _('Otro')

moneda = models.ForeignKey(Moneda, ...)  # USD o VES

# IGTF solo aplica en pagos en divisas
if pago.moneda.codigo_iso == 'USD':
    aplicar_igtf = True
```

### Reportes por Moneda

```python
# Ventas en USD
ventas_usd = Venta.objects.filter(moneda__codigo_iso='USD')

# Ventas en VES
ventas_ves = Venta.objects.filter(moneda__codigo_iso='VES')

# Pagos por método y moneda
pagos_zelle = PagoVenta.objects.filter(
    metodo='ZEL',
    moneda__codigo_iso='USD'
)
```

---

## 👥 CLIENTE vs PASAJERO

### Definiciones

- **Cliente**: Quien paga (modelo `Cliente`)
- **Pasajero**: Quien disfruta del servicio (modelo `Pasajero`)

### Relaciones

```python
class Venta(models.Model):
    cliente = ForeignKey(Cliente)  # Quien paga
    pasajeros = ManyToManyField(Pasajero)  # Quienes viajan
```

### Casos de Uso

1. **Cliente = Pasajero**: Persona compra para sí misma
2. **Cliente ≠ Pasajero**: Empresa compra para empleados
3. **1 Cliente, N Pasajeros**: Familia (padre paga, todos viajan)

---

## 🚢 CRUCEROS

### Componentes de Costo

```python
class CruceroReserva(models.Model):
    # Tarifa base
    tarifa_base_cabina = DecimalField(...)
    
    # Paquetes adicionales
    costo_paquete_bebidas = DecimalField(...)
    costo_paquete_restaurantes = DecimalField(...)
    costo_paquete_spa = DecimalField(...)
    costo_paquete_wifi = DecimalField(...)
    
    # Comisión
    es_comisionable = BooleanField(default=True)
    porcentaje_comision = DecimalField(...)  # 10-15% típico
    monto_comision = DecimalField(...)  # Auto-calculado
    
    # Fee agencia
    fee_servicio_agencia = DecimalField(...)
    
    # Totales
    costo_total_proveedor = DecimalField(...)
    precio_venta_cliente = DecimalField(...)
```

### Cálculo

```python
# Total proveedor
costo_total_proveedor = (
    tarifa_base_cabina
    + costo_paquete_bebidas
    + costo_paquete_restaurantes
    + costo_paquete_spa
    + costo_paquete_wifi
)

# Comisión
if es_comisionable:
    monto_comision = tarifa_base_cabina * (porcentaje_comision / 100)

# Precio al cliente
precio_venta_cliente = (
    costo_total_proveedor
    + fee_servicio_agencia
) * 1.03  # IGTF 3%

# Pago al proveedor
pago_proveedor = costo_total_proveedor - monto_comision

# Margen agencia
margen = monto_comision + fee_servicio_agencia
```

---

## 📊 REPORTES

### Por Tipo de Servicio

```python
# Boletos
boletos = SegmentoVuelo.objects.filter(
    venta__fecha_venta__range=[fecha_inicio, fecha_fin]
)

# Hoteles
hoteles = AlojamientoReserva.objects.filter(
    venta__fecha_venta__range=[fecha_inicio, fecha_fin]
)

# Cruceros
cruceros = CruceroReserva.objects.filter(
    fecha_embarque__range=[fecha_inicio, fecha_fin]
)
```

### Por Proveedor

```python
from django.db.models import Sum, Count

# Ventas por proveedor
reporte = ItemVenta.objects.filter(
    venta__fecha_venta__year=2025
).values(
    'proveedor_servicio__nombre'
).annotate(
    total_ventas=Count('id_item_venta'),
    monto_total=Sum('total_item_venta'),
    comision_total=Sum('comision_agencia_monto')
)
```

### Por Aerolínea (Boletos)

```python
from core.models_catalogos import Aerolinea

# Ventas por aerolínea
reporte = SegmentoVuelo.objects.filter(
    venta__fecha_venta__year=2025
).values(
    'aerolinea'
).annotate(
    total_segmentos=Count('id_segmento_vuelo'),
    total_ventas=Count('venta', distinct=True)
)

# Con RIF de aerolínea
for item in reporte:
    try:
        aerolinea = Aerolinea.objects.get(nombre__icontains=item['aerolinea'])
        item['rif'] = aerolinea.rif
    except:
        item['rif'] = 'N/A'
```

---

## ✅ Checklist de Implementación

### Boletos
- [ ] Agregar campos de costos en SegmentoVuelo
- [ ] Implementar cálculo de IGTF
- [ ] Agregar campos de anulación
- [ ] Crear reporte por aerolínea

### Servicios Terrestres
- [ ] Agregar flag `es_comisionable` en todos los modelos
- [ ] Agregar `porcentaje_comision` y `monto_comision`
- [ ] Agregar `fee_agencia`
- [ ] Implementar cálculo automático

### Cruceros
- [x] Modelo CruceroReserva creado
- [ ] Migración aplicada
- [ ] Admin configurado
- [ ] Serializers y Views

### Reportes
- [ ] Reporte por tipo de servicio
- [ ] Reporte por proveedor
- [ ] Reporte por aerolínea
- [ ] Reporte por moneda (USD/VES)

---

**Última actualización**: 24 de Enero de 2025  
**Estado**: Documentación completa  
**Autor**: Amazon Q Developer
