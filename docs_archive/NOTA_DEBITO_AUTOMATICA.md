# Generación Automática de Nota de Débito por Diferencial Cambiario

## Resumen

Se ha implementado la generación automática de **Notas de Débito** por IVA sobre ganancias cambiarias, cumpliendo con la normativa fiscal venezolana que establece que las ganancias cambiarias incrementan la base imponible del IVA.

## Marco Legal

Según la normativa tributaria venezolana:
- Las ganancias cambiarias constituyen un incremento en la base imponible
- Debe emitirse una Nota de Débito al cliente por el IVA adicional
- El IVA se calcula al 16% sobre la ganancia cambiaria en bolívares

## Funcionamiento Automático

### Flujo Completo

```
1. Cliente paga factura en USD
   ↓
2. Sistema detecta diferencia entre tasa factura vs tasa pago
   ↓
3. Si hay GANANCIA cambiaria (tasa subió):
   ↓
4. Sistema genera automáticamente:
   - Nota de Débito con IVA 16% sobre ganancia
   - Asiento contable completo
   - Registro en cuentas por cobrar
```

### Ejemplo Práctico

**Escenario:**
- Factura emitida: $100 USD
- Tasa BCV factura: 45.00 BSD/USD → 4,500 BSD
- Cliente paga 5 días después
- Tasa BCV pago: 47.00 BSD/USD → 4,700 BSD
- **Ganancia cambiaria: 200 BSD**

**Sistema genera automáticamente:**

1. **Nota de Débito ND-2025-000001**
   - Ganancia cambiaria: 200 BSD
   - IVA 16%: 32 BSD
   - Total a cobrar adicional: 32 BSD

2. **Asiento Contable del Pago:**
```
DÉBITO:   Bancos USD                    $100 / 4,700 BSD
CRÉDITO:  Cuentas por Cobrar            $100 / 4,500 BSD (histórico)
CRÉDITO:  Ingreso Diferencial Cambiario        200 BSD

DÉBITO:   Cuentas por Cobrar                    32 BSD (ND)
CRÉDITO:  IVA Débito Fiscal por Pagar           32 BSD
```

## Modelo de Datos

### NotaDebitoVenezuela

```python
class NotaDebitoVenezuela(models.Model):
    numero_nota_debito          # ND-YYYY-NNNNNN (auto)
    factura_origen              # FK a FacturaVenezuela
    fecha_emision               # Fecha de generación
    ganancia_cambiaria_bsd      # Monto ganancia en BSD
    monto_iva_bsd               # IVA 16% sobre ganancia
    tasa_factura                # Tasa BCV original
    tasa_pago                   # Tasa BCV al pago
    referencia_pago             # Ref del pago origen
    estado                      # EMITIDA / COBRADA / ANULADA
```

## Integración con Contabilidad

El servicio `ContabilidadService` maneja todo automáticamente:

```python
# En registrar_pago_y_diferencial()
if diferencial_bsd > 0:  # Ganancia
    # 1. Registra ganancia cambiaria
    # 2. Genera Nota de Débito
    nota_debito = _generar_nota_debito_diferencial(...)
    
    # 3. Registra IVA en asiento
    #    - Débito: Cuentas por Cobrar
    #    - Crédito: IVA Débito Fiscal
```

## Administración Django

### Visualización de Notas de Débito

En el admin: **Core → Notas de Débito Venezuela**

Campos visibles:
- Número de Nota de Débito
- Factura Origen
- Fecha Emisión
- Ganancia Cambiaria BSD
- Monto IVA BSD
- Estado

### Restricciones de Seguridad

- ❌ **No se pueden crear manualmente** (solo automáticas)
- ❌ **No se pueden eliminar** (solo superusuarios)
- ✅ Se pueden consultar y cambiar estado
- ✅ Trazabilidad completa con auditoría

## Consultas y Reportes

### Listar Notas de Débito Pendientes

```python
from core.models.facturacion_venezuela import NotaDebitoVenezuela

pendientes = NotaDebitoVenezuela.objects.filter(
    estado=NotaDebitoVenezuela.EstadoNotaDebito.EMITIDA
)

for nd in pendientes:
    print(f"{nd.numero_nota_debito}: {nd.monto_iva_bsd} BSD")
```

### Total IVA por Cobrar (Diferencial)

```python
from django.db.models import Sum

total_iva = NotaDebitoVenezuela.objects.filter(
    estado=NotaDebitoVenezuela.EstadoNotaDebito.EMITIDA
).aggregate(
    total=Sum('monto_iva_bsd')
)['total'] or 0

print(f"IVA pendiente por diferencial: {total_iva} BSD")
```

## Casos Especiales

### Pérdida Cambiaria (Tasa Baja)

Si la tasa BCV **baja** entre factura y pago:
- Se registra **pérdida cambiaria** (gasto)
- **NO se genera Nota de Débito**
- No hay IVA adicional a cobrar

### Múltiples Pagos Parciales

Si una factura se paga en varios pagos:
- Cada pago genera su propio diferencial
- Se crea una Nota de Débito por cada pago con ganancia
- Cada ND tiene su propia referencia al pago origen

### Tolerancia de Cálculo

- Diferencias menores a **0.01 BSD** se ignoran
- Evita generar NDs por redondeos insignificantes

## Impacto Fiscal

### Libro de Ventas

Las Notas de Débito deben registrarse en el Libro de Ventas:
- Como documento fiscal independiente
- Con su propio número correlativo
- Incrementando la base imponible del período

### Declaración de IVA

El IVA de las Notas de Débito:
- Se suma al IVA Débito Fiscal del mes
- Debe declararse en la forma 30 del SENIAT
- Incrementa el IVA por pagar del período

## Ventajas del Sistema Automático

1. ✅ **Cero errores de cálculo**: Matemática precisa garantizada
2. ✅ **Cumplimiento normativo**: Sigue exactamente la ley
3. ✅ **Trazabilidad completa**: Cada ND vinculada a su origen
4. ✅ **Auditoría integrada**: Registro automático en contabilidad
5. ✅ **Tiempo real**: Se genera al momento del pago
6. ✅ **Sin intervención manual**: Proceso 100% automatizado

## Monitoreo y Alertas

### Log de Generación

Cada Nota de Débito genera un log:

```
INFO: Nota de Débito ND-2025-000001 generada: 
      Ganancia 200.00 BSD, IVA 32.00 BSD
```

### Verificación de Integridad

El sistema valida:
- Que la ganancia sea > 0.01 BSD
- Que el IVA sea exactamente 16% de la ganancia
- Que la factura origen exista y sea válida
- Que el pago esté confirmado

## Próximas Mejoras

1. **Generación de PDF** para Nota de Débito
2. **Envío automático por email** al cliente
3. **Dashboard de NDs pendientes** de cobro
4. **Integración con sistema de cobranza**
5. **Reportes fiscales** específicos para NDs

## Soporte Técnico

- Modelo: `core/models/facturacion_venezuela.py`
- Servicio: `contabilidad/services.py` → `_generar_nota_debito_diferencial()`
- Admin: `core/admin_venezuela.py` → `NotaDebitoVenezuelaAdmin`
- Migración: `core/migrations/0016_add_nota_debito_venezuela.py`

---

**Estado**: ✅ Implementado y Funcional  
**Versión**: 1.0  
**Fecha**: Enero 2025  
**Cumplimiento**: Normativa Fiscal Venezolana (Ley IVA)
