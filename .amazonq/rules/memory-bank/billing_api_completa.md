# API de Facturación Completa - TravelHub

**Fecha**: 24 de Octubre de 2025  
**Estado**: ✅ Sistema completo implementado

---

## 📋 Funcionalidades Implementadas

### 1. Configuración de Imprenta Digital

**Modelo**: `Agencia`

Campos agregados:
- `imprenta_digital_nombre` - Razón Social de la Imprenta Digital Autorizada
- `imprenta_digital_rif` - RIF de la Imprenta Digital
- `imprenta_digital_providencia` - Número de Providencia SENIAT
- `es_sujeto_pasivo_especial` - Contribuyente Especial
- `esta_inscrita_rtn` - Inscrita en Registro Turístico Nacional

**Configuración**:
```python
# Actualizar datos de agencia
agencia = Agencia.objects.get(id=1)
agencia.imprenta_digital_nombre = "Imprenta Digital XYZ, C.A."
agencia.imprenta_digital_rif = "J-55555555-5"
agencia.imprenta_digital_providencia = "SNAT/2024/000123"
agencia.es_sujeto_pasivo_especial = True
agencia.save()
```

---

### 2. Doble Facturación Automática

**Servicio**: `core/services/doble_facturacion.py`

#### Método Principal: `generar_facturas_venta()`

Genera dos facturas automáticamente:

1. **Factura por Cuenta de Terceros**
   - Documenta el costo del servicio (boleto, hotel)
   - Identifica al proveedor con RIF
   - Leyenda Art. 10 Ley IVA
   - NO sujeta a retención ISLR

2. **Factura por Servicios Propios**
   - Documenta el fee de la agencia
   - Cálculo automático de IVA:
     - Nacional: 16% sobre 100% del fee
     - Internacional: 16% sobre 20% del fee (80% no sujeto)
   - SÍ sujeta a retención ISLR (5%)

#### Uso:

```python
from core.services.doble_facturacion import DobleFacturacionService
from decimal import Decimal

# Datos del tercero (aerolínea, hotel, etc.)
datos_tercero = {
    'razon_social': 'American Airlines',
    'rif': 'J-002537663',
    'monto_servicio': Decimal('1000.00'),
    'descripcion': 'Boleto aéreo CCS-MIA, Pasajero: Juan Pérez',
    'es_nacional': False  # True para nacional, False para internacional
}

# Fee de la agencia
fee_servicio = Decimal('100.00')

# Generar ambas facturas
factura_tercero, factura_propia = DobleFacturacionService.generar_facturas_venta(
    venta=venta,
    datos_tercero=datos_tercero,
    fee_servicio=fee_servicio
)
```

#### Método desde Boleto: `generar_desde_boleto()`

```python
# Generar desde boleto importado
factura_tercero, factura_propia = DobleFacturacionService.generar_desde_boleto(
    venta=venta,
    boleto_importado=boleto,
    fee_servicio=Decimal('100.00')
)
```

---

### 3. Endpoints API

#### POST `/api/facturas-consolidadas/doble_facturacion/`

Genera doble facturación automática.

**Request**:
```json
{
  "venta_id": 123,
  "datos_tercero": {
    "razon_social": "American Airlines",
    "rif": "J-002537663",
    "monto_servicio": "1000.00",
    "descripcion": "Boleto aéreo CCS-MIA, Pasajero: Juan Pérez",
    "es_nacional": false
  },
  "fee_servicio": "100.00"
}
```

**Response**:
```json
{
  "message": "Doble facturación generada exitosamente",
  "factura_tercero": {
    "id_factura": 9,
    "numero_factura": "F-20251024-0009",
    "tipo_operacion": "INTERMEDIACION",
    "tercero_razon_social": "American Airlines",
    "tercero_rif": "J-002537663",
    "subtotal_exento": "1000.00",
    "monto_total": "1000.00"
  },
  "factura_propia": {
    "id_factura": 10,
    "numero_factura": "F-20251024-0010",
    "tipo_operacion": "INTERMEDIACION",
    "subtotal_base_gravada": "20.00",
    "subtotal_exento": "80.00",
    "monto_iva_16": "3.20",
    "monto_total": "103.20"
  }
}
```

#### POST `/api/facturas-consolidadas/{id}/generar_pdf/`

Genera PDF de la factura.

**Response**:
```json
{
  "message": "PDF generado exitosamente",
  "factura": { ... }
}
```

#### POST `/api/facturas-consolidadas/{id}/contabilizar/`

Genera asiento contable.

**Response**:
```json
{
  "message": "Factura contabilizada exitosamente",
  "factura": { ... }
}
```

#### POST `/api/facturas-consolidadas/{id}/recalcular/`

Recalcula totales de la factura.

#### GET `/api/facturas-consolidadas/pendientes/`

Obtiene facturas con saldo pendiente.

---

## 📊 Ejemplo Completo: Venta de Boleto Internacional

### Escenario:
- Boleto CCS-MAD: USD 1,000.00
- Fee agencia: USD 100.00
- Tasa BCV: Bs. 36.50

### Código:

```python
from core.services.doble_facturacion import DobleFacturacionService
from core.models import Venta
from decimal import Decimal

# Obtener venta
venta = Venta.objects.get(id_venta=123)

# Datos del tercero
datos_tercero = {
    'razon_social': 'Iberia Airlines',
    'rif': 'J-12345678-9',
    'monto_servicio': Decimal('1000.00'),
    'descripcion': 'Boleto aéreo CCS-MAD, Pasajero: Juan Pérez, Vuelo IB6251',
    'es_nacional': False
}

# Generar facturas
factura_tercero, factura_propia = DobleFacturacionService.generar_facturas_venta(
    venta=venta,
    datos_tercero=datos_tercero,
    fee_servicio=Decimal('100.00')
)

# Generar PDFs
from core.services.factura_pdf_generator import guardar_pdf_factura
guardar_pdf_factura(factura_tercero)
guardar_pdf_factura(factura_propia)

print(f"Factura Tercero: {factura_tercero.numero_factura}")
print(f"Factura Propia: {factura_propia.numero_factura}")
```

### Resultado:

**Factura 1: Por Cuenta de Terceros (F-20251024-0009)**
```
Servicio prestado por: Iberia Airlines - RIF: J-12345678-9
Descripción: Boleto aéreo CCS-MAD, Pasajero: Juan Pérez, Vuelo IB6251
Base Exenta: USD 1,000.00
TOTAL: USD 1,000.00
Equivalente: Bs. 36,500.00

Leyenda: "SE EMITE DE CONFORMIDAD CON EL ARTÍCULO 10 DE LA LEY DE IVA"
```

**Factura 2: Por Servicios Propios (F-20251024-0010)**
```
Descripción: Fee por servicio de intermediación internacional
Base Imponible (16%): USD 20.00 (20% del fee)
Monto No Sujeto: USD 80.00 (80% del fee)
IVA (16% s/ 20.00): USD 3.20
TOTAL A PAGAR: USD 103.20
Equivalente: Bs. 3,766.80

Nota ISLR: Monto sujeto a retención de ISLR (5%): USD 100.00
```

**Retención ISLR del Cliente**:
- Base: USD 100.00 (fee completo)
- Retención 5%: USD 5.00
- Pago neto a agencia: USD 98.20

---

## 🎯 Cálculos Automáticos

### Servicio Nacional
```python
fee = Decimal('100.00')
base_gravada = fee  # 100%
iva = base_gravada * Decimal('0.16')  # USD 16.00
total = fee + iva  # USD 116.00
```

### Servicio Internacional
```python
fee = Decimal('100.00')
base_gravada = fee * Decimal('0.20')  # USD 20.00 (20%)
base_no_sujeta = fee * Decimal('0.80')  # USD 80.00 (80%)
iva = base_gravada * Decimal('0.16')  # USD 3.20
total = fee + iva  # USD 103.20
```

---

## 📚 Archivos del Sistema

### Modelos
- `core/models/agencia.py` - Configuración de imprenta digital
- `core/models/facturacion_consolidada.py` - Facturas consolidadas

### Servicios
- `core/services/doble_facturacion.py` - Doble facturación automática
- `core/services/factura_pdf_generator.py` - Generación de PDFs
- `core/services/factura_contabilidad.py` - Integración contable

### Views
- `core/views/factura_consolidada_views.py` - API REST

### Templates
- `core/templates/facturas/factura_consolidada_pdf.html` - Plantilla PDF

---

## ✅ Checklist de Uso

### Para Generar Doble Facturación:

1. [ ] Crear venta en el sistema
2. [ ] Configurar datos de imprenta digital en agencia
3. [ ] Preparar datos del tercero (aerolínea, hotel)
4. [ ] Definir fee de servicio
5. [ ] Llamar a `DobleFacturacionService.generar_facturas_venta()`
6. [ ] Generar PDFs de ambas facturas
7. [ ] Entregar factura de tercero al cliente (para su contabilidad)
8. [ ] Entregar factura propia al cliente (para pago del fee)
9. [ ] Cliente aplica retención ISLR solo sobre factura propia

---

## 🚨 Errores Comunes a Evitar

1. **No identificar al tercero**
   - ❌ Omitir RIF y razón social
   - ✅ Siempre incluir datos completos del tercero

2. **Calcular IVA incorrectamente**
   - ❌ IVA sobre 100% del fee internacional
   - ✅ IVA sobre 20% del fee internacional

3. **Permitir retención sobre factura de tercero**
   - ❌ Cliente retiene sobre ambas facturas
   - ✅ Cliente retiene solo sobre factura propia

4. **No generar ambas facturas**
   - ❌ Factura única por monto total
   - ✅ Siempre dos facturas separadas

---

**Última actualización**: 24 de Octubre de 2025  
**Estado**: ✅ Sistema completo y funcional  
**Autor**: Amazon Q Developer
