# Libro de Ventas - Implementado ✅

**Fecha**: 24 de Octubre de 2025  
**Estado**: Completamente funcional

---

## 📋 Funcionalidad Implementada

Sistema completo de Libro de Ventas para declaración de IVA según normativa SENIAT.

### Características:

1. **Separación de Operaciones**
   - Ventas propias (débito fiscal de la agencia)
   - Ventas por cuenta de terceros (sin débito fiscal)

2. **Bases Imponibles**
   - Base gravada 16%
   - Base exenta
   - Base exportación (0%)

3. **Impuestos**
   - IVA 16%
   - IVA adicional (divisas)
   - IGTF 3%

4. **Cálculo Automático**
   - Débito fiscal total
   - Totales por tipo de operación
   - Resumen del período

---

## 🚀 Uso

### 1. Comando de Terminal

#### Generar por mes:
```bash
python manage.py generar_libro_ventas --mes 10 --anio 2025
```

#### Generar por rango de fechas:
```bash
python manage.py generar_libro_ventas --fecha-inicio 2025-10-01 --fecha-fin 2025-10-31
```

#### Exportar a CSV:
```bash
python manage.py generar_libro_ventas --mes 10 --anio 2025 --formato csv --archivo libro_ventas_octubre.csv
```

### 2. API REST

#### Generar libro de ventas (JSON):
```http
GET /api/libro-ventas/generar/?fecha_inicio=2025-10-01&fecha_fin=2025-10-31
Authorization: Bearer <token>
```

**Response**:
```json
{
  "periodo": {
    "fecha_inicio": "2025-10-01",
    "fecha_fin": "2025-10-31"
  },
  "ventas_propias": [
    {
      "fecha": "2025-10-24",
      "numero_factura": "F-20251024-0008",
      "numero_control": "00000008",
      "cliente_rif": "V12345678",
      "cliente_nombre": "Juan Pérez",
      "base_gravada": "100.00",
      "base_exenta": "0.00",
      "base_exportacion": "0.00",
      "iva_16": "16.00",
      "iva_adicional": "0.00",
      "igtf": "0.00",
      "total": "116.00",
      "tipo_operacion": "Intermediación"
    }
  ],
  "ventas_terceros": [],
  "totales": {
    "propias": {
      "base_gravada": "100.00",
      "base_exenta": "0.00",
      "base_exportacion": "0.00",
      "iva_16": "16.00",
      "iva_adicional": "0.00",
      "igtf": "0.00",
      "total": "116.00"
    },
    "terceros": {
      "base_exenta": "0.00",
      "total": "0.00"
    }
  },
  "resumen": {
    "total_facturas": 1,
    "facturas_propias": 1,
    "facturas_terceros": 0,
    "debito_fiscal": "16.00"
  }
}
```

#### Exportar a CSV:
```http
GET /api/libro-ventas/generar/?fecha_inicio=2025-10-01&fecha_fin=2025-10-31&formato=csv
Authorization: Bearer <token>
```

Descarga archivo CSV con formato SENIAT.

#### Resumen mensual:
```http
GET /api/libro-ventas/resumen_mensual/?mes=10&anio=2025
Authorization: Bearer <token>
```

**Response**:
```json
{
  "periodo": {
    "mes": 10,
    "anio": 2025,
    "fecha_inicio": "2025-10-01",
    "fecha_fin": "2025-10-31"
  },
  "resumen": {
    "total_facturas": 1,
    "facturas_propias": 1,
    "facturas_terceros": 0,
    "debito_fiscal": "16.00"
  },
  "totales": { ... }
}
```

---

## 📊 Formato CSV

El archivo CSV generado incluye:

### Columnas:
1. Fecha
2. Número Factura
3. Número Control
4. RIF Cliente
5. Nombre Cliente
6. Base Gravada
7. Base Exenta
8. Base Exportación
9. IVA 16%
10. IVA Adicional
11. IGTF
12. Total
13. Tipo Operación
14. RIF Tercero
15. Nombre Tercero

### Secciones:
- Detalle de ventas propias
- Detalle de ventas por cuenta de terceros
- Totales ventas propias
- Totales ventas terceros
- **Débito fiscal total (IVA a declarar)**

---

## 🎯 Ejemplo de Salida en Consola

```
================================================================================
LIBRO DE VENTAS
Período: 2025-10-01 al 2025-10-31
================================================================================

VENTAS PROPIAS:
2025-10-24 | F-20251024-0008 | Juan Pérez | Base: $100.00 | IVA: $16.00 | Total: $116.00

VENTAS POR CUENTA DE TERCEROS:
2025-10-24 | F-20251024-0009 | Juan Pérez | Tercero: American Airlines | Total: $1000.00

================================================================================
TOTALES:
Total Facturas: 2
  - Ventas Propias: 1
  - Ventas Terceros: 1

VENTAS PROPIAS:
  Base Gravada:    $      100.00
  Base Exenta:     $        0.00
  Base Exportación:$        0.00
  IVA 16%:         $       16.00
  IVA Adicional:   $        0.00
  IGTF:            $        0.00
  Total:           $      116.00

VENTAS TERCEROS:
  Base Exenta:     $     1000.00
  Total:           $     1000.00

DÉBITO FISCAL TOTAL (IVA A DECLARAR):
  $       16.00
================================================================================
```

---

## 📁 Archivos del Sistema

### Servicio
- `core/services/libro_ventas.py` - Lógica de generación

### Views
- `core/views/libro_ventas_views.py` - API REST

### Comando
- `core/management/commands/generar_libro_ventas.py` - CLI

### URLs
- Registrado en `core/urls.py` como `libro-ventas`

---

## ✅ Cumplimiento Normativo

### Providencia 0071 SENIAT:
- ✅ Separación de operaciones propias vs terceros
- ✅ Identificación de terceros con RIF
- ✅ Desglose de bases imponibles
- ✅ Cálculo correcto de débito fiscal

### Ley de IVA:
- ✅ Art. 10 - Facturación por cuenta de terceros
- ✅ Art. 3 - Principio de territorialidad
- ✅ Alícuota general 16%

---

## 🎓 Casos de Uso

### 1. Declaración Mensual de IVA
```bash
# Generar libro del mes anterior
python manage.py generar_libro_ventas --mes 9 --anio 2025 --formato csv

# Usar el CSV para llenar formulario SENIAT
```

### 2. Auditoría Interna
```bash
# Revisar ventas del trimestre
python manage.py generar_libro_ventas --fecha-inicio 2025-07-01 --fecha-fin 2025-09-30
```

### 3. Conciliación Contable
```bash
# Verificar débito fiscal vs libro mayor
python manage.py generar_libro_ventas --mes 10 --anio 2025
```

---

## 🚀 Próximas Mejoras Opcionales

1. **Libro de Compras** (para crédito fiscal)
2. **Conciliación automática** con declaración SENIAT
3. **Alertas** de inconsistencias
4. **Exportación** a formato XML SENIAT
5. **Dashboard** visual de IVA

---

**Última actualización**: 24 de Octubre de 2025  
**Estado**: ✅ Completamente funcional  
**Autor**: Amazon Q Developer
