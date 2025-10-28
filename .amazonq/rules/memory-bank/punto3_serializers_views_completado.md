# Punto 3: Serializers y Views - Completado ✅

**Fecha**: 23 de Octubre de 2025  
**Estado**: Implementado y funcional

---

## 📋 Archivos Creados

### 1. Serializers
**Archivo**: `core/serializers_facturacion_consolidada.py`

- `ItemFacturaConsolidadaSerializer` - Items con tipos de servicio
- `DocumentoExportacionConsolidadoSerializer` - Documentos de exportación
- `FacturaConsolidadaSerializer` - Factura completa con:
  - Nested serializers (items, documentos)
  - Display fields (estado, tipo operación, moneda)
  - Create/Update con items anidados
  - Read-only fields (cálculos automáticos)

### 2. Views
**Archivo**: `core/views/factura_consolidada_views.py`

- `FacturaConsolidadaViewSet` - CRUD completo con:
  - Autenticación: JWT + Session + Token
  - Búsqueda: número, control, cliente, RIF
  - Ordenamiento: fecha, número, monto
  - Select/prefetch optimizado
  - Actions personalizadas:
    - `recalcular/` - Recalcular totales
    - `pendientes/` - Facturas con saldo

- `ItemFacturaConsolidadaViewSet` - CRUD de items

### 3. URLs
**Archivo**: `core/urls.py` (actualizado)

Registrados en el router:
- `facturas-consolidadas`
- `items-factura-consolidada`

---

## 🎯 Endpoints Disponibles

### Facturas Consolidadas

```
GET    /api/facturas-consolidadas/
POST   /api/facturas-consolidadas/
GET    /api/facturas-consolidadas/{id}/
PUT    /api/facturas-consolidadas/{id}/
PATCH  /api/facturas-consolidadas/{id}/
DELETE /api/facturas-consolidadas/{id}/

# Actions
POST   /api/facturas-consolidadas/{id}/recalcular/
GET    /api/facturas-consolidadas/pendientes/
```

### Items de Factura

```
GET    /api/items-factura-consolidada/
POST   /api/items-factura-consolidada/
GET    /api/items-factura-consolidada/{id}/
PUT    /api/items-factura-consolidada/{id}/
DELETE /api/items-factura-consolidada/{id}/
```

---

## 📊 Campos del Serializer

### FacturaConsolidadaSerializer

**Campos básicos**:
- `id_factura`, `numero_factura`, `numero_control`
- `venta_asociada`, `cliente`, `moneda`
- `fecha_emision`, `fecha_vencimiento`

**Emisor (agencia)**:
- `emisor_rif`, `emisor_razon_social`, `emisor_direccion_fiscal`
- `es_sujeto_pasivo_especial`, `esta_inscrita_rtn`

**Cliente**:
- `cliente_es_residente`, `cliente_identificacion`, `cliente_direccion`

**Tipo de operación**:
- `tipo_operacion` (VENTA_PROPIA, INTERMEDIACION)
- `tipo_operacion_display`

**Moneda y cambio**:
- `moneda_operacion` (BOLIVAR, DIVISA)
- `tasa_cambio_bcv`

**Bases imponibles (USD)**:
- `subtotal_base_gravada`, `subtotal_exento`, `subtotal_exportacion`

**Impuestos (USD)**:
- `monto_iva_16`, `monto_iva_adicional`, `monto_igtf`

**Totales (USD)**:
- `subtotal`, `monto_total`, `saldo_pendiente`

**Equivalentes en Bolívares**:
- `subtotal_base_gravada_bs`, `subtotal_exento_bs`
- `monto_iva_16_bs`, `monto_igtf_bs`, `monto_total_bs`

**Intermediación**:
- `tercero_rif`, `tercero_razon_social`

**Digital**:
- `modalidad_emision`, `firma_digital`

**Estado**:
- `estado`, `estado_display`

**Archivos**:
- `archivo_pdf`

**Relaciones**:
- `items_factura` (nested)
- `documentos_exportacion` (nested)
- `cliente_detalle` (nested)
- `moneda_detalle` (nested)

---

## 🔍 Búsqueda y Filtros

### Búsqueda (search)
```
?search=F-20250920
?search=J-12345678
?search=Juan Perez
```

Campos buscables:
- `numero_factura`
- `numero_control`
- `cliente__nombre`
- `cliente__rif_cedula`
- `emisor_rif`

### Ordenamiento (ordering)
```
?ordering=-fecha_emision
?ordering=monto_total
?ordering=-numero_factura
```

Campos ordenables:
- `fecha_emision`
- `numero_factura`
- `monto_total`

---

## 💡 Ejemplo de Uso

### Crear Factura con Items

```json
POST /api/facturas-consolidadas/

{
  "cliente": 1,
  "moneda": 1,
  "tipo_operacion": "VENTA_PROPIA",
  "moneda_operacion": "DIVISA",
  "tasa_cambio_bcv": 36.50,
  "emisor_rif": "J-12345678-9",
  "emisor_razon_social": "Mi Agencia C.A.",
  "items_factura": [
    {
      "descripcion": "Boleto aéreo CCS-MIA",
      "cantidad": 1,
      "precio_unitario": 500.00,
      "tipo_servicio": "TRANSPORTE_AEREO_NACIONAL",
      "es_gravado": false,
      "nombre_pasajero": "Juan Perez",
      "numero_boleto": "2357120126507"
    },
    {
      "descripcion": "Hotel 3 noches",
      "cantidad": 3,
      "precio_unitario": 100.00,
      "tipo_servicio": "ALOJAMIENTO_Y_OTROS_GRAVADOS",
      "es_gravado": true,
      "alicuota_iva": 16.00
    }
  ]
}
```

### Respuesta

```json
{
  "id_factura": 8,
  "numero_factura": "F-20251023-0008",
  "numero_control": "00000008",
  "cliente": 1,
  "cliente_detalle": {
    "id_cliente": 1,
    "nombres": "Juan",
    "apellidos": "Perez"
  },
  "subtotal_base_gravada": 300.00,
  "subtotal_exento": 500.00,
  "monto_iva_16": 48.00,
  "monto_total": 848.00,
  "subtotal_base_gravada_bs": 10950.00,
  "monto_total_bs": 30952.00,
  "items_factura": [...]
}
```

---

## ✅ Verificación

```bash
# Verificar registro de ViewSets
python manage.py shell -c "from core.urls import router; print([url.name for url in router.urls if 'consolidada' in url.name])"

# Verificar facturas migradas
python manage.py shell -c "from core.models import FacturaConsolidada; print(f'Total: {FacturaConsolidada.objects.count()}')"
```

**Resultado**: 7 facturas migradas exitosamente

---

## 🎯 Próximos Pasos

- **Punto 4**: Actualizar frontend con formulario completo
- **Punto 5**: Generar PDF con formato legal venezolano
- **Punto 6**: Integración contable automática
- **Punto 7**: Deprecar modelos antiguos

---

**Última actualización**: 23 de Octubre de 2025  
**Estado**: ✅ Completado y funcional  
**Autor**: Amazon Q Developer
