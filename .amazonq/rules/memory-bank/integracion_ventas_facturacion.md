# Integración Ventas - Facturación Consolidada

**Fecha**: 24 de Enero de 2025  
**Estado**: ✅ Implementado

---

## 📋 Cambios Realizados

### 1. Campo en Modelo Venta

Agregado campo `factura_consolidada` al modelo `Venta`:

```python
# core/models/ventas.py
class Venta(models.Model):
    # ... campos existentes ...
    
    factura = models.ForeignKey('core.Factura', on_delete=models.SET_NULL, 
                               blank=True, null=True, related_name='ventas', 
                               verbose_name=_("Factura Asociada (Legacy)"))
    
    factura_consolidada = models.ForeignKey('core.FacturaConsolidada', 
                                           on_delete=models.SET_NULL, 
                                           blank=True, null=True, 
                                           related_name='ventas_facturadas', 
                                           verbose_name=_("Factura Consolidada"))
```

### 2. Relación Bidireccional

**Venta → FacturaConsolidada**:
- Campo: `venta.factura_consolidada`
- Related name: `ventas_facturadas`

**FacturaConsolidada → Venta**:
- Campo: `factura.venta_asociada`
- Related name: `facturas_consolidadas`

---

## 🚀 Uso

### Crear Factura desde Venta

```python
from core.models import Venta, FacturaConsolidada, ItemFacturaConsolidada
from decimal import Decimal

# Obtener venta
venta = Venta.objects.get(localizador='VTA-20250124-0001')

# Crear factura consolidada
factura = FacturaConsolidada.objects.create(
    venta_asociada=venta,
    cliente=venta.cliente,
    moneda=venta.moneda,
    tipo_operacion='VENTA_PROPIA',
    moneda_operacion='DIVISA',
    emisor_rif='J-12345678-9',
    emisor_razon_social='Mi Agencia C.A.',
    emisor_direccion_fiscal='Av. Principal, Caracas',
    cliente_identificacion=venta.cliente.rif_cedula,
    cliente_es_residente=True,
    tasa_cambio_bcv=Decimal('36.50')
)

# Crear items desde items de venta
for item_venta in venta.items_venta.all():
    ItemFacturaConsolidada.objects.create(
        factura=factura,
        descripcion=item_venta.descripcion_personalizada or item_venta.producto_servicio.nombre,
        cantidad=item_venta.cantidad,
        precio_unitario=item_venta.precio_unitario_venta,
        tipo_servicio='ALOJAMIENTO_Y_OTROS_GRAVADOS',
        es_gravado=True,
        alicuota_iva=Decimal('16.00')
    )

# Vincular factura a venta
venta.factura_consolidada = factura
venta.save()
```

### Consultar Facturas de una Venta

```python
# Obtener venta
venta = Venta.objects.get(localizador='VTA-20250124-0001')

# Factura consolidada (nueva)
if venta.factura_consolidada:
    print(f"Factura: {venta.factura_consolidada.numero_factura}")
    print(f"Total: {venta.factura_consolidada.monto_total}")

# Todas las facturas consolidadas relacionadas
facturas = venta.facturas_consolidadas.all()
for factura in facturas:
    print(f"{factura.numero_factura}: {factura.monto_total}")
```

### Consultar Ventas de una Factura

```python
# Obtener factura
factura = FacturaConsolidada.objects.get(numero_factura='F-20250124-0001')

# Venta principal asociada
if factura.venta_asociada:
    print(f"Venta: {factura.venta_asociada.localizador}")
    print(f"Cliente: {factura.venta_asociada.cliente.nombre}")

# Todas las ventas que tienen esta factura
ventas = factura.ventas_facturadas.all()
for venta in ventas:
    print(f"{venta.localizador}: {venta.total_venta}")
```

---

## 🔄 Flujo Completo: Venta → Factura

### 1. Crear Venta

```python
from core.models import Venta, ItemVenta, ProductoServicio
from personas.models import Cliente
from core.models_catalogos import Moneda

# Crear venta
venta = Venta.objects.create(
    cliente=Cliente.objects.get(id_cliente=1),
    moneda=Moneda.objects.get(codigo_iso='USD'),
    tipo_venta='B2C',
    descripcion_general='Paquete turístico CCS-MIA'
)

# Agregar items
ItemVenta.objects.create(
    venta=venta,
    producto_servicio=ProductoServicio.objects.get(tipo_producto='HTL'),
    descripcion_personalizada='Hotel 3 noches Miami',
    cantidad=3,
    precio_unitario_venta=Decimal('100.00')
)

# Recalcular finanzas
venta.recalcular_finanzas()
```

### 2. Generar Factura Consolidada

```python
from core.services.doble_facturacion import DobleFacturacionService

# Opción A: Factura simple
factura = FacturaConsolidada.objects.create(
    venta_asociada=venta,
    cliente=venta.cliente,
    moneda=venta.moneda,
    tipo_operacion='VENTA_PROPIA',
    moneda_operacion='DIVISA',
    emisor_rif='J-12345678-9',
    emisor_razon_social='Mi Agencia C.A.',
    emisor_direccion_fiscal='Av. Principal',
    cliente_identificacion=venta.cliente.rif_cedula,
    tasa_cambio_bcv=Decimal('36.50')
)

# Crear items
for item in venta.items_venta.all():
    ItemFacturaConsolidada.objects.create(
        factura=factura,
        descripcion=item.descripcion_personalizada,
        cantidad=item.cantidad,
        precio_unitario=item.precio_unitario_venta,
        tipo_servicio='ALOJAMIENTO_Y_OTROS_GRAVADOS',
        es_gravado=True
    )

# Vincular
venta.factura_consolidada = factura
venta.save()

# Opción B: Doble facturación (boletos)
if venta.segmentos_vuelo.exists():
    datos_tercero = {
        'razon_social': 'American Airlines',
        'rif': 'E-99000001-1',
        'monto_servicio': Decimal('1000.00'),
        'descripcion': 'Boleto aéreo CCS-MIA',
        'es_nacional': False
    }
    
    factura_tercero, factura_propia = DobleFacturacionService.generar_facturas_venta(
        venta=venta,
        datos_tercero=datos_tercero,
        fee_servicio=Decimal('100.00')
    )
    
    venta.factura_consolidada = factura_propia
    venta.save()
```

### 3. Generar PDF

```python
from core.services.factura_pdf_generator import guardar_pdf_factura

# Generar PDF
guardar_pdf_factura(factura)

# Verificar
print(f"PDF: {factura.archivo_pdf.url}")
```

### 4. Contabilizar

```python
from core.services.factura_contabilidad import generar_asiento_factura

# Generar asiento contable
asiento = generar_asiento_factura(factura)

# Verificar
print(f"Asiento: {asiento.numero_asiento}")
print(f"Débito: {asiento.total_debito}")
print(f"Crédito: {asiento.total_credito}")
```

---

## 📊 Queries Útiles

### Ventas sin Facturar

```python
from core.models import Venta

ventas_sin_factura = Venta.objects.filter(
    factura_consolidada__isnull=True,
    estado__in=['PAG', 'COM']
)

for venta in ventas_sin_factura:
    print(f"{venta.localizador}: {venta.total_venta}")
```

### Facturas de un Cliente

```python
from personas.models import Cliente

cliente = Cliente.objects.get(id_cliente=1)

# Facturas directas
facturas = FacturaConsolidada.objects.filter(cliente=cliente)

# Facturas desde ventas
facturas_ventas = FacturaConsolidada.objects.filter(
    venta_asociada__cliente=cliente
)

# Todas
todas = facturas | facturas_ventas
```

### Reporte de Facturación

```python
from django.db.models import Sum, Count
from core.models import FacturaConsolidada

# Por mes
reporte = FacturaConsolidada.objects.filter(
    fecha_emision__year=2025,
    fecha_emision__month=1
).aggregate(
    total_facturas=Count('id_factura'),
    total_monto=Sum('monto_total'),
    total_iva=Sum('monto_iva_16')
)

print(f"Facturas: {reporte['total_facturas']}")
print(f"Monto: ${reporte['total_monto']}")
print(f"IVA: ${reporte['total_iva']}")
```

---

## ✅ Beneficios

1. **Trazabilidad**: Cada factura sabe de qué venta proviene
2. **Doble vínculo**: Venta → Factura y Factura → Venta
3. **Compatibilidad**: Mantiene campo legacy `factura` para migración gradual
4. **Flexibilidad**: Una venta puede tener múltiples facturas (doble facturación)
5. **Integridad**: Relaciones con `SET_NULL` para no perder datos

---

## 🔄 Migración Gradual

### Fase 1: Dual (Actual)
- Ambos campos coexisten: `factura` (legacy) y `factura_consolidada` (nuevo)
- Nuevas ventas usan `factura_consolidada`
- Ventas antiguas mantienen `factura`

### Fase 2: Migración de Datos
```python
# Script de migración
from core.models import Venta, FacturaConsolidada

for venta in Venta.objects.filter(factura__isnull=False, factura_consolidada__isnull=True):
    # Migrar factura antigua a consolidada
    # (requiere lógica específica según estructura)
    pass
```

### Fase 3: Deprecación
- Marcar `factura` como deprecado
- Agregar warnings en código
- Documentar que usar `factura_consolidada`

### Fase 4: Eliminación
- Después de 3-6 meses, eliminar campo `factura`
- Eliminar modelo `Factura` antiguo

---

**Última actualización**: 24 de Enero de 2025  
**Estado**: ✅ Integración completada  
**Autor**: Amazon Q Developer
