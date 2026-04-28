# Retenciones ISLR - Implementado ✅

**Fecha**: 24 de Octubre de 2025  
**Estado**: Completamente funcional

---

## 📋 Funcionalidad Implementada

Sistema completo de gestión de Retenciones de ISLR según Decreto 1.808 y normativa SENIAT.

### Características:

1. **Registro de Comprobantes**
   - Número de comprobante único
   - Fecha de emisión y operación
   - Vinculación con factura
   - Archivo PDF del comprobante

2. **Tipos de Operación**
   - Honorarios Profesionales (HP)
   - Servicios No Mercantiles (SNM)
   - Comisiones Mercantiles (CM) - Más común para agencias
   - Otros (OT)

3. **Cálculos Automáticos**
   - Base imponible
   - Porcentaje de retención (5% por defecto)
   - Monto retenido (calculado automáticamente)

4. **Estados**
   - Pendiente (PEN) - Recién registrada
   - Aplicada (APL) - Aplicada en declaración anual
   - Anulada (ANU) - Comprobante anulado

---

## 🚀 Uso

### 1. Registrar Retención en Admin

1. Ir a Admin Django → Retenciones ISLR
2. Click "Agregar Retención ISLR"
3. Completar datos:
   - Número de comprobante
   - Factura relacionada
   - Cliente (agente de retención)
   - Base imponible
   - Porcentaje (5% por defecto)
4. Guardar

### 2. Comando de Terminal

#### Generar reporte mensual:
```bash
python manage.py reporte_retenciones --mes 10 --anio 2025
```

#### Generar reporte por rango:
```bash
python manage.py reporte_retenciones --fecha-inicio 2025-10-01 --fecha-fin 2025-10-31
```

#### Filtrar por estado:
```bash
python manage.py reporte_retenciones --mes 10 --anio 2025 --estado PEN
```

#### Exportar a CSV:
```bash
python manage.py reporte_retenciones --mes 10 --anio 2025 --formato csv --archivo retenciones_octubre.csv
```

### 3. Programáticamente

```python
from core.models.retenciones_islr import RetencionISLR
from decimal import Decimal

# Registrar retención
retencion = RetencionISLR.objects.create(
    numero_comprobante="RET-2025-001",
    factura=factura,
    cliente=cliente,
    fecha_operacion=factura.fecha_emision,
    tipo_operacion='CM',  # Comisiones Mercantiles
    codigo_concepto='03-04',
    base_imponible=factura.subtotal,
    porcentaje_retencion=Decimal('5.00'),
    # monto_retenido se calcula automáticamente
)
```

---

## 📊 Ejemplo de Salida

### Reporte en Consola:

```
================================================================================
REPORTE DE RETENCIONES ISLR
Período: 2025-10-01 al 2025-10-31
================================================================================

POR TIPO DE OPERACIÓN:

Comisiones Mercantiles:
  Cantidad: 1
  Base Imponible: $500.00
  Monto Retenido: $25.00

DETALLE:
2025-10-24 | RET-2025-001 | Armando Alemán | Base: $500.00 | Ret: $25.00 | Pendiente

================================================================================
TOTALES:
Total Retenciones: 1
Base Imponible Total: $500.00
Monto Retenido Total: $25.00
================================================================================
```

### CSV Exportado:

```csv
Número Comprobante;Fecha Emisión;Cliente;Factura;Tipo Operación;Base Imponible;Porcentaje;Monto Retenido;Estado
RET-2025-001;24/10/2025;Armando Alemán;F-20251024-0008;Comisiones Mercantiles;500.00;5.00;25.00;Pendiente

TOTALES
;;;;;500.00;;25.00;
```

---

## 🎯 Casos de Uso

### 1. Declaración Anual de ISLR

```bash
# Generar reporte del año fiscal
python manage.py reporte_retenciones --fecha-inicio 2025-01-01 --fecha-fin 2025-12-31 --formato csv

# Usar CSV para llenar formulario ARC
```

### 2. Conciliación Mensual

```bash
# Verificar retenciones recibidas vs facturas emitidas
python manage.py reporte_retenciones --mes 10 --anio 2025
```

### 3. Seguimiento de Comprobantes Pendientes

```bash
# Ver retenciones pendientes de aplicar
python manage.py reporte_retenciones --mes 10 --anio 2025 --estado PEN
```

---

## 📁 Archivos del Sistema

### Modelo
- `core/models/retenciones_islr.py` - Modelo de datos

### Admin
- `core/admin.py` - Admin de Django (línea con RetencionISLRAdmin)

### Servicio
- `core/services/reporte_retenciones.py` - Lógica de reportes

### Comando
- `core/management/commands/reporte_retenciones.py` - CLI

---

## ✅ Cumplimiento Normativo

### Decreto 1.808:
- ✅ Registro de comprobantes de retención
- ✅ Porcentajes correctos (5% PJ a PJ)
- ✅ Base imponible correcta (fee antes de IVA)
- ✅ Vinculación con factura

### Buenas Prácticas:
- ✅ Archivo PDF del comprobante
- ✅ Trazabilidad completa
- ✅ Estados para control
- ✅ Reportes para declaración

---

## 🔗 Integración con Facturación

### Relación con Facturas:

```python
# Obtener retenciones de una factura
factura = FacturaConsolidada.objects.get(numero_factura='F-20251024-0008')
retenciones = factura.retenciones_islr.all()

# Total retenido
total_retenido = retenciones.aggregate(Sum('monto_retenido'))['monto_retenido__sum']
```

### Flujo Completo:

1. Agencia emite factura por servicios propios (fee)
2. Cliente paga y practica retención 5%
3. Cliente entrega comprobante de retención
4. Agencia registra comprobante en sistema
5. Al final del año, agencia usa reporte para declaración ARC

---

## 💡 Tips

### Porcentajes de Retención Comunes:

| Tipo de Operación | PJ a PJ | PJ a PN |
|-------------------|---------|---------|
| Comisiones Mercantiles | 5% | 3% |
| Honorarios Profesionales | 5% | 3% |
| Servicios No Mercantiles | 5% | 3% |

### Códigos de Concepto SENIAT:

- **03-04**: Comisiones Mercantiles
- **03-05**: Honorarios Profesionales
- **03-06**: Servicios No Mercantiles

---

## 🚀 Próximas Mejoras Opcionales

1. **Alertas automáticas** cuando cliente no entrega comprobante
2. **Conciliación automática** factura vs retención
3. **Generación de ARC** (declaración anual)
4. **Dashboard visual** de retenciones
5. **Notificaciones** de comprobantes pendientes

---

**Última actualización**: 24 de Octubre de 2025  
**Estado**: ✅ Completamente funcional  
**Autor**: Amazon Q Developer
