# Sistema de Contabilidad Integrada para Venezuela (VEN-NIF)

## Resumen Ejecutivo

Se ha implementado un módulo de contabilidad completo que cumple con el marco normativo venezolano (VEN-NIF) para agencias de viajes, integrándose automáticamente con el sistema de facturación existente.

## Características Principales

### 1. Dualidad Monetaria (USD/BSD)

El sistema maneja dos monedas simultáneamente según VEN-NIF:

- **Moneda Funcional (USD)**: Dólar estadounidense para gestión y toma de decisiones
- **Moneda de Presentación (BSD)**: Bolívar para cumplimiento legal y fiscal

Cada asiento contable registra montos en ambas monedas automáticamente.

### 2. Gestión de Tasas de Cambio BCV

- Tabla `TasaCambioBCV` almacena historial diario de tasas oficiales
- Comando de gestión para actualizar tasas manualmente
- Consulta automática de tasa del día para cada transacción
- Fallback a tasa más reciente si no existe para fecha específica

### 3. Integración Automática Facturación → Contabilidad

El sistema genera asientos contables automáticamente al:

#### a) Crear una Factura
- Detecta si es operación de **INTERMEDIACIÓN** (Agente) o **VENTA PROPIA** (Principal)
- Genera asiento con cuentas apropiadas según tipo de operación
- Registra IVA e IGTF automáticamente

**Ejemplo Intermediación (Agente)**:
```
DÉBITO:   Cuentas por Cobrar Clientes (USD)
CRÉDITO:  Ingresos por Comisiones
CRÉDITO:  Cuentas por Pagar Proveedor
CRÉDITO:  IVA Débito Fiscal por Pagar
CRÉDITO:  IGTF por Pagar (si aplica)
```

**Ejemplo Venta Propia (Principal)**:
```
DÉBITO:   Cuentas por Cobrar Clientes (USD)
CRÉDITO:  Ingresos por Venta de Paquetes
CRÉDITO:  IVA Débito Fiscal por Pagar
CRÉDITO:  IGTF por Pagar (si aplica)
```

#### b) Registrar un Pago
- Calcula diferencial cambiario automáticamente
- Compara tasa de factura vs tasa de pago
- Registra ganancia o pérdida cambiaria

**Ejemplo con Ganancia Cambiaria**:
```
DÉBITO:   Bancos (USD)
CRÉDITO:  Cuentas por Cobrar (al valor histórico)
CRÉDITO:  Ingreso por Diferencial Cambiario (solo BSD)
```

**Ejemplo con Pérdida Cambiaria**:
```
DÉBITO:   Bancos (USD)
DÉBITO:   Pérdida por Diferencial Cambiario (solo BSD)
CRÉDITO:  Cuentas por Cobrar (al valor histórico)
```

### 4. Contribución INATUR (1%)

Proceso automatizado para provisionar la contribución parafiscal mensual:

- Calcula 1% sobre ingresos brutos del mes en BSD
- Genera asiento de provisión automáticamente
- Comando de gestión para ejecutar al cierre de mes

```
DÉBITO:   Gasto Contribución INATUR
CRÉDITO:  Contribución INATUR por Pagar
```

## Estructura de Datos

### Modelos Principales

1. **PlanContable**: Catálogo de cuentas contables
   - Jerarquía de cuentas (niveles)
   - Clasificación por tipo (Activo, Pasivo, Patrimonio, Ingreso, Gasto)
   - Naturaleza (Deudora/Acreedora)

2. **AsientoContable**: Registro de transacciones
   - Fecha contable y tipo de asiento
   - Referencia a documento fuente
   - Tasa de cambio aplicada
   - Totales debe/haber calculados

3. **DetalleAsiento**: Líneas del asiento
   - Cuenta contable
   - Montos en USD (debe/haber)
   - Montos en BSD (debe_bsd/haber_bsd)
   - Descripción de la línea

4. **TasaCambioBCV**: Historial de tasas
   - Fecha de vigencia
   - Tasa BSD/USD
   - Fuente (BCV, API, Manual)

## Comandos de Gestión

### Actualizar Tasa BCV
```bash
# Tasa para hoy
python manage.py actualizar_tasa_bcv --tasa 45.50

# Tasa para fecha específica
python manage.py actualizar_tasa_bcv --tasa 45.50 --fecha 2025-01-15

# Con fuente personalizada
python manage.py actualizar_tasa_bcv --tasa 45.50 --fuente "API BCV"
```

### Provisionar INATUR
```bash
# Mes/año actual
python manage.py provisionar_inatur

# Mes/año específico
python manage.py provisionar_inatur --mes 12 --anio 2024
```

## Plan de Cuentas Incluido

Se incluye un plan de cuentas básico adaptado a agencias de viajes venezolanas:

### Activos
- 1.1.01.02 - Caja General (USD)
- 1.1.01.04 - Bancos Nacionales (USD)
- 1.1.02.02 - Cuentas por Cobrar Clientes (USD)

### Pasivos
- 2.1.01.02 - Cuentas por Pagar Proveedores (USD)
- 2.1.02.01 - IVA Débito Fiscal por Pagar
- 2.1.02.02 - Contribución INATUR por Pagar
- 2.1.02.03 - IGTF por Pagar

### Ingresos
- 4.1.01 - Comisiones por Venta de Boletos Aéreos
- 4.2 - Ingresos por Venta de Paquetes
- 7.1.01 - Ingreso por Diferencial Cambiario

### Gastos
- 6.1.05 - Gasto Contribución INATUR
- 7.2.01 - Pérdida por Diferencial Cambiario

## Carga Inicial

```bash
# 1. Aplicar migraciones
python manage.py migrate contabilidad

# 2. Cargar plan de cuentas
python manage.py loaddata plan_cuentas_venezuela.json

# 3. Cargar tasa BCV inicial
python manage.py actualizar_tasa_bcv --tasa 45.50
```

## Flujo de Trabajo Típico

### Escenario: Venta de Boleto Aéreo (Intermediación)

1. **Usuario crea factura en el admin**
   - Tipo Operación: INTERMEDIACION
   - Moneda: DIVISA (USD)
   - Subtotal Base Gravada: $100 (comisión)
   - IVA 16%: $16
   - Total: $116

2. **Sistema genera asiento automáticamente** (vía señal)
   - Consulta tasa BCV del día (ej: 45.00)
   - Crea asiento tipo VENTAS
   - Registra:
     - Débito: Cuentas por Cobrar $116 / 5,220 BSD
     - Crédito: Comisiones $100 / 4,500 BSD
     - Crédito: IVA $16 / 720 BSD

3. **Cliente paga 3 días después**
   - Usuario registra pago de $116
   - Tasa BCV del día: 47.00 (devaluación)

4. **Sistema calcula diferencial cambiario**
   - BSD factura: $116 × 45.00 = 5,220 BSD
   - BSD pago: $116 × 47.00 = 5,452 BSD
   - Diferencial: 232 BSD (ganancia)

5. **Sistema genera asiento de pago**
   - Débito: Bancos $116 / 5,452 BSD
   - Crédito: Cuentas por Cobrar $116 / 5,220 BSD (histórico)
   - Crédito: Ingreso Diferencial Cambiario 232 BSD

6. **Al final del mes**
   - Ejecutar: `python manage.py provisionar_inatur --mes 1 --anio 2025`
   - Sistema calcula 1% sobre ingresos totales en BSD
   - Genera asiento de provisión

## Consideraciones Importantes

### Diferencial Cambiario e IVA
Según normativa venezolana, las ganancias cambiarias incrementan la base imponible del IVA. El sistema:
- Detecta ganancias cambiarias
- Registra en log la necesidad de emitir Nota de Débito
- **PENDIENTE**: Generación automática de Nota de Débito (próxima iteración)

### Moneda Funcional vs Presentación
- **Gestión interna**: Usar siempre USD (moneda funcional)
- **Reportes legales**: Sistema convierte automáticamente a BSD
- **Libros oficiales**: Se presentan en BSD según Código de Comercio

### Ajuste por Inflación
- Venezuela es economía hiperinflacionaria (NIC 29)
- Al usar USD como moneda funcional, se evita re-expresión compleja
- El efecto inflacionario se captura en el diferencial cambiario

## Próximos Pasos Recomendados

1. ✅ **Generación automática de Nota de Débito** por IVA sobre ganancia cambiaria (COMPLETADO - Ver NOTA_DEBITO_AUTOMATICA.md)
2. ✅ **API de integración con BCV** para actualización automática de tasas (COMPLETADO - Ver CONFIGURAR_SINCRONIZACION_BCV.md)
3. ✅ **Reportes contables** (COMPLETADO - Ver REPORTES_CONTABLES.md):
   - Balance de Comprobación
   - Estado de Resultados
   - Balance General
   - Libro Diario / Mayor
4. ✅ **Cierre contable mensual** automatizado (COMPLETADO - Ver CIERRE_MENSUAL.md)
5. **Conciliación bancaria** integrada
6. **Exportación a formatos fiscales** (XML SENIAT)

## Soporte y Documentación

- Código fuente: `contabilidad/`
- Servicios: `contabilidad/services.py`
- Señales: `contabilidad/signals.py`
- Comandos: `contabilidad/management/commands/`
- Fixtures: `fixtures/plan_cuentas_venezuela.json`

## Cumplimiento Normativo

✅ Código de Comercio (Libros Diario, Mayor)  
✅ VEN-NIF PYME (Dualidad monetaria)  
✅ NIC 21 (Moneda extranjera)  
✅ Ley IVA (Registro de impuestos)  
✅ IGTF (Impuesto 3% sobre divisas)  
✅ INATUR (Contribución 1% turismo)  
✅ BA VEN-NIF 2 (Economía hiperinflacionaria)  

---

**Versión**: 1.0  
**Fecha**: Enero 2025  
**Marco Normativo**: VEN-NIF PYME + Código de Comercio Venezuela
