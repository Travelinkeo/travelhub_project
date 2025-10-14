# Reportes Contables VEN-NIF

## Resumen

Sistema completo de reportes contables que cumple con VEN-NIF y Código de Comercio venezolano. Genera Balance de Comprobación, Estado de Resultados, Balance General, Libro Diario y Libro Mayor en USD y BSD.

## Reportes Disponibles

### 1. Balance de Comprobación

Muestra todas las cuentas con movimientos en un período, con sus saldos deudores y acreedores.

**Comando**:
```bash
python manage.py generar_reporte balance_comprobacion --desde 2025-01-01 --hasta 2025-01-31
python manage.py generar_reporte balance_comprobacion --desde 2025-01-01 --hasta 2025-01-31 --moneda BSD
```

**Salida**:
```
=== BALANCE DE COMPROBACIÓN 2025-01-01 a 2025-01-31 (USD) ===

Código       Cuenta                                   Debe            Haber           Saldo
====================================================================================================
1.1.01.04    Bancos Nacionales (USD)              10,000.00            0.00       10,000.00
1.1.02.02    Cuentas por Cobrar Clientes           5,000.00        3,000.00        2,000.00
4.1.01       Comisiones Boletos Aéreos                 0.00        5,000.00       -5,000.00
====================================================================================================
TOTALES                                           15,000.00       15,000.00
```

**URL Web**: `/contabilidad/reportes/balance-comprobacion/?desde=2025-01-01&hasta=2025-01-31&moneda=USD`

### 2. Estado de Resultados (P&L)

Muestra ingresos, gastos y utilidad neta del período.

**Comando**:
```bash
python manage.py generar_reporte estado_resultados --desde 2025-01-01 --hasta 2025-01-31
```

**Salida**:
```
=== ESTADO DE RESULTADOS 2025-01-01 a 2025-01-31 (USD) ===

Ingresos:           15,000.00
Gastos:              8,500.00
========================================
Utilidad Neta:       6,500.00
```

**URL Web**: `/contabilidad/reportes/estado-resultados/?desde=2025-01-01&hasta=2025-01-31`

### 3. Balance General

Estado de situación financiera a una fecha específica (Activos = Pasivos + Patrimonio).

**Comando**:
```bash
python manage.py generar_reporte balance_general --fecha 2025-01-31
```

**Salida**:
```
=== BALANCE GENERAL al 2025-01-31 (USD) ===

Activos:        25,000.00
Pasivos:        10,000.00
Patrimonio:     15,000.00
========================================
Total P+P:      25,000.00

[OK] Balance cuadrado
```

**URL Web**: `/contabilidad/reportes/balance-general/?fecha=2025-01-31`

### 4. Libro Diario

Registro cronológico de todos los asientos contables del período.

**Comando**:
```bash
python manage.py generar_reporte libro_diario --desde 2025-01-01 --hasta 2025-01-31
```

**Salida**:
```
=== LIBRO DIARIO 2025-01-01 a 2025-01-31 (USD) ===

Asiento: ASI-2025-0001 | Fecha: 2025-01-15 | Ventas
Descripción: Factura FACT-2025-0123 - Cliente ABC
--------------------------------------------------------------------------------
  1.1.02.02 Cuentas por Cobrar Clientes              1,000.00
      4.1.01 Comisiones Boletos Aéreos                         900.00
      2.1.02.01 IVA Débito Fiscal por Pagar                    100.00
Total:                                                1,000.00 = 1,000.00
```

**URL Web**: `/contabilidad/reportes/libro-diario/?desde=2025-01-01&hasta=2025-01-31`

### 5. Libro Mayor

Movimientos detallados de una cuenta específica con saldo acumulado.

**Comando**:
```bash
# Primero obtener ID de cuenta desde admin
python manage.py generar_reporte libro_mayor --cuenta 7 --desde 2025-01-01 --hasta 2025-01-31
```

**URL Web**: `/contabilidad/reportes/libro-mayor/?cuenta=7&desde=2025-01-01&hasta=2025-01-31`

## Uso desde Código Python

### Balance de Comprobación

```python
from datetime import date
from contabilidad.reportes import ReportesContables

resultado = ReportesContables.balance_comprobacion(
    fecha_desde=date(2025, 1, 1),
    fecha_hasta=date(2025, 1, 31),
    moneda='USD'
)

print(f"Total Debe: {resultado['totales']['debe']}")
print(f"Total Haber: {resultado['totales']['haber']}")

for cuenta in resultado['cuentas']:
    print(f"{cuenta['codigo']} - {cuenta['nombre']}: {cuenta['saldo']}")
```

### Estado de Resultados

```python
resultado = ReportesContables.estado_resultados(
    fecha_desde=date(2025, 1, 1),
    fecha_hasta=date(2025, 1, 31),
    moneda='USD'
)

print(f"Ingresos: {resultado['ingresos']}")
print(f"Gastos: {resultado['gastos']}")
print(f"Utilidad: {resultado['utilidad_neta']}")
```

### Balance General

```python
resultado = ReportesContables.balance_general(
    fecha_corte=date(2025, 1, 31),
    moneda='USD'
)

print(f"Activos: {resultado['activos']}")
print(f"Pasivos: {resultado['pasivos']}")
print(f"Patrimonio: {resultado['patrimonio']}")
print(f"Cuadrado: {resultado['cuadrado']}")
```

### Libro Diario

```python
asientos = ReportesContables.libro_diario(
    fecha_desde=date(2025, 1, 1),
    fecha_hasta=date(2025, 1, 31),
    moneda='USD'
)

for asiento in asientos:
    print(f"Asiento {asiento['numero']}: {asiento['descripcion']}")
    for detalle in asiento['detalles']:
        print(f"  {detalle['cuenta_nombre']}: {detalle['debe']} / {detalle['haber']}")
```

### Libro Mayor

```python
resultado = ReportesContables.libro_mayor(
    cuenta_id=7,  # ID de la cuenta
    fecha_desde=date(2025, 1, 1),
    fecha_hasta=date(2025, 1, 31),
    moneda='USD'
)

print(f"Cuenta: {resultado['cuenta']['codigo']} - {resultado['cuenta']['nombre']}")
print(f"Saldo Inicial: {resultado['saldo_inicial']}")

for mov in resultado['movimientos']:
    print(f"{mov['fecha']} - {mov['descripcion']}: Saldo {mov['saldo']}")

print(f"Saldo Final: {resultado['saldo_final']}")
```

## Características

### Dualidad Monetaria

Todos los reportes soportan USD y BSD:
- `--moneda USD`: Moneda funcional (gestión)
- `--moneda BSD`: Moneda de presentación (legal)

### Filtros de Fecha

- **Período**: `--desde` y `--hasta` para reportes de flujo
- **Corte**: `--fecha` para reportes de posición (Balance General)

### Solo Asientos Contabilizados

Los reportes solo incluyen asientos con estado `CONTABILIZADO`, ignorando borradores y anulados.

## Cumplimiento Normativo

| Reporte | Normativa | Cumplimiento |
|---------|-----------|--------------|
| Balance de Comprobación | Código de Comercio Art. 32 | ✅ |
| Estado de Resultados | VEN-NIF PYME Sección 5 | ✅ |
| Balance General | VEN-NIF PYME Sección 4 | ✅ |
| Libro Diario | Código de Comercio Art. 32 | ✅ |
| Libro Mayor | Código de Comercio Art. 32 | ✅ |

## Exportación (Próximamente)

### PDF
```bash
python manage.py generar_reporte balance_general --fecha 2025-01-31 --formato pdf
```

### Excel
```bash
python manage.py generar_reporte balance_comprobacion --desde 2025-01-01 --hasta 2025-01-31 --formato xlsx
```

### XML SENIAT
```bash
python manage.py generar_reporte libro_diario --desde 2025-01-01 --hasta 2025-01-31 --formato xml
```

## Automatización

### Reporte Mensual Automático

Crear script `generar_reportes_mensuales.bat`:

```batch
@echo off
set MES=%1
set ANIO=%2

python manage.py generar_reporte balance_comprobacion --desde %ANIO%-%MES%-01 --hasta %ANIO%-%MES%-31 > reportes\balance_%ANIO%_%MES%.txt
python manage.py generar_reporte estado_resultados --desde %ANIO%-%MES%-01 --hasta %ANIO%-%MES%-31 > reportes\pyg_%ANIO%_%MES%.txt
python manage.py generar_reporte balance_general --fecha %ANIO%-%MES%-31 > reportes\balance_general_%ANIO%_%MES%.txt
```

Ejecutar:
```bash
generar_reportes_mensuales.bat 01 2025
```

## Troubleshooting

### Error: "No hay movimientos"

**Causa**: No existen asientos contabilizados en el período.

**Solución**: Verificar que hay asientos con estado `CONTABILIZADO`.

### Error: "Balance descuadrado"

**Causa**: Asientos con debe ≠ haber.

**Solución**: Revisar asientos en Admin → Contabilidad → Asientos Contables.

### Diferencias USD vs BSD

**Causa**: Tasas de cambio diferentes en cada transacción.

**Solución**: Normal en economía con devaluación. Usar BSD para reportes legales.

## Próximas Mejoras

1. ✅ Reportes básicos (COMPLETADO)
2. **Exportación PDF/Excel**
3. **Gráficos y visualizaciones**
4. **Comparativos período anterior**
5. **Notas a los estados financieros**
6. **Consolidación multi-empresa**

---

**Estado**: ✅ Implementado y Funcional  
**Versión**: 1.0  
**Fecha**: Enero 2025  
**Cumplimiento**: VEN-NIF PYME + Código de Comercio
