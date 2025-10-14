# Implementación: Nota de Débito Automática por Diferencial Cambiario

## ✅ Estado: COMPLETADO

Se ha implementado exitosamente la generación automática de Notas de Débito por IVA sobre ganancias cambiarias.

## 📦 Componentes Implementados

### 1. Modelo de Datos

**Archivo**: `core/models/facturacion_venezuela.py`

```python
class NotaDebitoVenezuela(models.Model):
    numero_nota_debito          # Auto-generado: ND-YYYY-NNNNNN
    factura_origen              # FK a FacturaVenezuela
    ganancia_cambiaria_bsd      # Monto ganancia en BSD
    monto_iva_bsd               # IVA 16% calculado
    tasa_factura / tasa_pago    # Tasas BCV involucradas
    referencia_pago             # Trazabilidad al pago
    estado                      # EMITIDA / COBRADA / ANULADA
```

**Migración**: `core/migrations/0016_add_nota_debito_venezuela.py` ✅ Aplicada

### 2. Servicio de Generación

**Archivo**: `contabilidad/services.py`

Método `_generar_nota_debito_diferencial()`:
- Calcula IVA 16% sobre ganancia cambiaria
- Crea registro de NotaDebitoVenezuela
- Genera asiento contable completo
- Registra en cuentas por cobrar e IVA por pagar

### 3. Integración Automática

**Flujo en `registrar_pago_y_diferencial()`**:

```python
if diferencial_bsd > 0:  # Ganancia
    # 1. Registra ganancia cambiaria
    # 2. Genera Nota de Débito automáticamente
    nota_debito = _generar_nota_debito_diferencial(...)
    
    # 3. Registra IVA en asiento contable:
    #    DÉBITO:  Cuentas por Cobrar (IVA ND)
    #    CRÉDITO: IVA Débito Fiscal por Pagar
```

### 4. Administración

**Archivo**: `core/admin_venezuela.py`

`NotaDebitoVenezuelaAdmin`:
- Visualización completa de NDs generadas
- Filtros por estado y fecha
- Búsqueda por número, factura, referencia
- **Restricciones de seguridad**:
  - No creación manual (solo automática)
  - Solo superusuarios pueden eliminar
  - Trazabilidad completa

## 🔄 Flujo Completo Implementado

```
┌─────────────────────┐
│  Usuario registra   │
│  PagoVenta          │
└──────────┬──────────┘
           │
           │ Signal: post_save
           ▼
┌─────────────────────────────────┐
│  ContabilidadService            │
│  .registrar_pago_y_diferencial  │
└──────────┬──────────────────────┘
           │
           │ 1. Obtiene tasa pago
           │ 2. Compara con tasa factura
           │ 3. Calcula diferencial
           ▼
┌─────────────────────┐
│  ¿Ganancia > 0.01?  │
└──────────┬──────────┘
           │ SÍ
           ▼
┌─────────────────────────────────┐
│  _generar_nota_debito_diferencial│
└──────────┬──────────────────────┘
           │
           │ 1. Calcula IVA 16%
           │ 2. Crea NotaDebitoVenezuela
           │ 3. Registra en asiento
           ▼
┌─────────────────────┐
│  NotaDebitoVenezuela│
│  + AsientoContable  │
│  (IVA por cobrar)   │
└─────────────────────┘
```

## 📊 Ejemplo Real

### Datos de Entrada
- Factura: $100 USD
- Tasa factura: 45.00 BSD/USD → 4,500 BSD
- Tasa pago: 47.00 BSD/USD → 4,700 BSD
- **Ganancia: 200 BSD**

### Salida Automática

**1. Nota de Débito Generada**
```
Número: ND-2025-000001
Factura Origen: FACT-2025-0123
Ganancia Cambiaria: 200.00 BSD
IVA 16%: 32.00 BSD
Estado: EMITIDA
```

**2. Asiento Contable**
```
Fecha: 2025-01-15
Descripción: Pago PAGO-456 - Venta VTA-20250115-0001

Línea 1:
  DÉBITO:  Bancos USD                    $100 / 4,700 BSD
  
Línea 2:
  CRÉDITO: Cuentas por Cobrar            $100 / 4,500 BSD
  
Línea 3:
  CRÉDITO: Ingreso Diferencial Cambiario        200 BSD
  
Línea 4:
  DÉBITO:  Cuentas por Cobrar (ND)               32 BSD
  
Línea 5:
  CRÉDITO: IVA Débito Fiscal por Pagar           32 BSD
```

## 🧪 Pruebas Realizadas

### Test 1: Generación Básica
- ✅ Pago con ganancia cambiaria genera ND
- ✅ Número correlativo auto-generado
- ✅ IVA calculado correctamente (16%)

### Test 2: Asiento Contable
- ✅ Líneas de débito/crédito correctas
- ✅ Montos en BSD precisos
- ✅ Asiento cuadrado (debe = haber)

### Test 3: Trazabilidad
- ✅ ND vinculada a factura origen
- ✅ Referencia al pago que generó diferencial
- ✅ Tasas BCV registradas

### Test 4: Restricciones
- ✅ No se puede crear ND manualmente
- ✅ Solo superusuarios pueden eliminar
- ✅ Estados cambian correctamente

## 📈 Impacto Fiscal

### Libro de Ventas
- Cada ND se registra como documento fiscal independiente
- Incrementa base imponible del período
- Número correlativo propio

### Declaración IVA
- IVA de NDs suma al Débito Fiscal mensual
- Debe declararse en forma 30 SENIAT
- Incrementa IVA por pagar

### Cuentas por Cobrar
- Cada ND genera una cuenta por cobrar adicional
- Cliente debe pagar IVA sobre ganancia cambiaria
- Trazabilidad completa para cobranza

## 🔍 Validaciones Implementadas

1. ✅ Ganancia > 0.01 BSD (tolerancia redondeo)
2. ✅ IVA = Ganancia × 0.16 (exacto)
3. ✅ Factura origen existe y es válida
4. ✅ Pago está confirmado
5. ✅ Tasas BCV son válidas (> 0)
6. ✅ No duplicar NDs para mismo pago

## 📝 Logs Generados

```
INFO: Nota de Débito ND-2025-000001 generada: 
      Ganancia 200.00 BSD, IVA 32.00 BSD
      
INFO: Asiento de pago ASI-2025-0456 generado con diferencial 200.00 BSD
```

## 🎯 Cumplimiento Normativo

| Requisito | Estado |
|-----------|--------|
| Ley IVA Art. 28 (Base imponible) | ✅ |
| Ganancia cambiaria incrementa base | ✅ |
| Emisión de Nota de Débito | ✅ |
| IVA 16% sobre ganancia | ✅ |
| Registro en Libro de Ventas | ✅ |
| Trazabilidad completa | ✅ |

## 📚 Documentación Generada

- ✅ `NOTA_DEBITO_AUTOMATICA.md`: Guía completa de usuario
- ✅ `IMPLEMENTACION_NOTA_DEBITO.md`: Este documento técnico
- ✅ Actualización de `CONTABILIDAD_VENEZUELA_VEN_NIF.md`
- ✅ Actualización de `RESUMEN_CONTABILIDAD_VEN_NIF.md`

## 🚀 Próximos Pasos Sugeridos

1. **Generación de PDF** para Nota de Débito
2. **Envío automático por email** al cliente
3. **Dashboard de NDs pendientes**
4. **Integración con cobranza**
5. **Reportes fiscales específicos**

---

**Implementado por**: Sistema TravelHub  
**Fecha**: Enero 2025  
**Versión**: 1.0  
**Estado**: ✅ PRODUCCIÓN
