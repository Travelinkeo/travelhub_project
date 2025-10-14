# Cierre Contable Mensual Automatizado

## Resumen

Proceso automatizado para ejecutar el cierre contable mensual según VEN-NIF, incluyendo provisión INATUR, verificación de balance y cierre de resultados.

## Comando

```bash
# Cerrar mes anterior (automático)
python manage.py cierre_mensual

# Cerrar mes específico
python manage.py cierre_mensual --mes 1 --anio 2025

# Modo prueba (no guarda)
python manage.py cierre_mensual --mes 1 --anio 2025 --dry-run
```

## Proceso Automatizado

El comando ejecuta 4 pasos:

### 1. Provisión INATUR (1%)

Calcula y provisiona automáticamente la contribución del 1% sobre ingresos brutos del mes.

```
DÉBITO:  Gasto Contribución INATUR
CRÉDITO: Contribución INATUR por Pagar
```

### 2. Verificación de Balance

Valida que el balance esté cuadrado:
- Activos = Pasivos + Patrimonio
- Diferencia < 0.01 USD

Si está descuadrado, muestra la diferencia pero continúa.

### 3. Cierre de Resultados

Traslada la utilidad o pérdida del período a Resultados Acumulados:

**Si hay utilidad**:
```
CRÉDITO: Resultados Acumulados (Patrimonio)
```

**Si hay pérdida**:
```
DÉBITO: Resultados Acumulados (Patrimonio)
```

### 4. Resumen

Muestra el Estado de Resultados del mes:
- Ingresos totales
- Gastos totales
- Utilidad/Pérdida neta

## Ejemplo de Ejecución

```bash
python manage.py cierre_mensual --mes 1 --anio 2025
```

**Salida**:
```
=== CIERRE CONTABLE 01/2025 ===

1. Provisionando INATUR 1%...
   [OK]
2. Verificando balance...
   [OK] Balance cuadrado
3. Cerrando resultado del período...
   [OK]

=== RESUMEN ===
Ingresos:     15,000.00 USD
Gastos:        8,500.00 USD
Utilidad:      6,500.00 USD

[OK] Cierre completado
```

## Modo Dry-Run

Para simular sin guardar cambios:

```bash
python manage.py cierre_mensual --mes 1 --anio 2025 --dry-run
```

**Salida**:
```
=== CIERRE CONTABLE 01/2025 ===

1. Provisionando INATUR 1%...
   [OK]
2. Verificando balance...
   [OK] Balance cuadrado
3. Cerrando resultado del período...
   [OK]

=== RESUMEN ===
Ingresos:     15,000.00 USD
Gastos:        8,500.00 USD
Utilidad:      6,500.00 USD

[DRY-RUN] No se guardaron cambios
```

## Automatización Mensual

### Windows (Task Scheduler)

Crear tarea programada para ejecutar el primer día de cada mes:

**Programa**: `C:\Users\ARMANDO\travelhub_project\cierre_mensual.bat`

**Contenido de `cierre_mensual.bat`**:
```batch
@echo off
cd /d "%~dp0"
call venv\Scripts\activate.bat
python manage.py cierre_mensual >> logs\cierre_mensual.log 2>&1
```

**Configuración**:
- Frecuencia: Mensual
- Día: 1 de cada mes
- Hora: 00:00 AM

### Linux/macOS (Cron)

```bash
# Ejecutar el día 1 de cada mes a las 00:00
0 0 1 * * cd /ruta/proyecto && /ruta/venv/bin/python manage.py cierre_mensual >> logs/cierre_mensual.log 2>&1
```

## Validaciones

El comando valida:

1. ✅ Mes entre 1 y 12
2. ✅ Año válido
3. ✅ Existencia de cuenta Resultados Acumulados (3.2)
4. ✅ Balance cuadrado (con advertencia si no)
5. ✅ Transacción atómica (rollback si falla)

## Asientos Generados

### Asiento INATUR

```
Fecha: 2025-01-31
Tipo: AJUSTE
Referencia: INATUR-202501

Línea 1:
  DÉBITO:  6.1.05 Gasto Contribución INATUR    150.00 BSD
  
Línea 2:
  CRÉDITO: 2.1.02.02 INATUR por Pagar          150.00 BSD
```

### Asiento de Cierre

```
Fecha: 2025-01-31
Tipo: CIERRE
Referencia: CIERRE-202501

Línea 1:
  CRÉDITO: 3.2 Resultados Acumulados         6,500.00 USD
```

## Logs

Los logs se guardan en `logs/cierre_mensual.log`:

```
2025-02-01 00:00:01 INFO: Provisión INATUR 01/2025: 150.00 BSD
2025-02-01 00:00:02 INFO: Asiento de cierre ASI-2025-0050 generado
2025-02-01 00:00:03 INFO: Cierre mensual 01/2025 completado
```

## Troubleshooting

### Error: "No existe cuenta Resultados Acumulados"

**Causa**: Falta cuenta 3.2 en el plan de cuentas.

**Solución**: Crear cuenta en Admin → Contabilidad → Plan de Cuentas:
- Código: 3.2
- Nombre: Resultados Acumulados
- Tipo: Patrimonio
- Naturaleza: Acreedora

### Error: "Balance descuadrado"

**Causa**: Asientos con debe ≠ haber.

**Solución**: 
1. Revisar asientos en Admin → Asientos Contables
2. Filtrar por estado CONTABILIZADO
3. Verificar que `total_debe = total_haber`
4. Corregir asientos descuadrados

### Advertencia: "No hay utilidad/pérdida a cerrar"

**Causa**: Resultado del mes es 0.00 USD.

**Solución**: Normal si no hubo operaciones. No se genera asiento de cierre.

## Verificación Post-Cierre

### 1. Verificar Asientos Generados

```bash
python manage.py generar_reporte libro_diario --desde 2025-01-31 --hasta 2025-01-31
```

Debe mostrar:
- Asiento de provisión INATUR
- Asiento de cierre de resultados

### 2. Verificar Balance

```bash
python manage.py generar_reporte balance_general --fecha 2025-01-31
```

Debe estar cuadrado: Activos = Pasivos + Patrimonio

### 3. Verificar Resultados Acumulados

En Admin → Contabilidad → Plan de Cuentas → Resultados Acumulados:
- Debe reflejar la utilidad/pérdida del mes

## Reversión de Cierre

Si necesitas revertir un cierre:

1. Identificar asientos de cierre:
```sql
SELECT * FROM contabilidad_asientocontable 
WHERE tipo_asiento = 'CIE' 
AND fecha_contable = '2025-01-31';
```

2. Cambiar estado a ANULADO en Admin

3. Volver a ejecutar cierre si es necesario

## Mejores Prácticas

1. ✅ **Ejecutar dry-run primero**: Validar antes de guardar
2. ✅ **Revisar balance**: Asegurar que esté cuadrado
3. ✅ **Backup previo**: Respaldar DB antes del cierre
4. ✅ **Verificar post-cierre**: Validar asientos generados
5. ✅ **Documentar**: Guardar logs de cada cierre

## Próximas Mejoras

1. **Cierre de cuentas de resultado**: Saldar ingresos y gastos a cero
2. **Ajuste por inflación**: Aplicar BA VEN-NIF 2 si aplica
3. **Notificaciones**: Email al completar cierre
4. **Dashboard**: Visualización de cierres históricos
5. **Validaciones adicionales**: Conciliaciones pendientes

---

**Estado**: ✅ Implementado y Funcional  
**Versión**: 1.0  
**Fecha**: Enero 2025  
**Cumplimiento**: VEN-NIF PYME + Código de Comercio
