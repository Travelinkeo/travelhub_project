# Configuración: Sincronización Automática de Tasa BCV

## Resumen

El sistema puede obtener automáticamente la tasa de cambio oficial del BCV desde su sitio web, eliminando la necesidad de actualización manual diaria.

## Componentes

### 1. Cliente BCV (`contabilidad/bcv_client.py`)

Realiza scraping del sitio web oficial del BCV para extraer la tasa USD/BSD actual.

**Características**:
- Timeout de 10 segundos
- Manejo robusto de errores
- Logging detallado
- Extracción mediante BeautifulSoup

### 2. Comando de Gestión

```bash
# Sincronizar tasa actual
python manage.py sincronizar_tasa_bcv

# Modo prueba (no guarda)
python manage.py sincronizar_tasa_bcv --dry-run
```

## Configuración Automática (Windows)

### Opción 1: Task Scheduler (Recomendado)

**Paso 1**: Abrir Task Scheduler
- Presionar `Win + R`
- Escribir `taskschd.msc`
- Enter

**Paso 2**: Crear Tarea Básica
- Clic derecho en "Biblioteca del Programador de tareas"
- "Crear tarea básica..."

**Paso 3**: Configurar Tarea
- **Nombre**: `Sincronizar Tasa BCV`
- **Descripción**: `Actualiza tasa de cambio BCV diariamente`
- **Desencadenador**: Diariamente
- **Hora**: `09:00 AM` (después de que BCV actualice)
- **Acción**: Iniciar un programa
- **Programa**: `C:\Users\ARMANDO\travelhub_project\sincronizar_bcv.bat`
- **Iniciar en**: `C:\Users\ARMANDO\travelhub_project`

**Paso 4**: Configuración Avanzada
- Marcar "Ejecutar con los privilegios más altos"
- Marcar "Ejecutar tanto si el usuario inició sesión como si no"
- En "Configurar para": Windows 10

### Opción 2: Cron (Linux/macOS)

```bash
# Editar crontab
crontab -e

# Agregar línea (ejecutar diariamente a las 9 AM)
0 9 * * * cd /ruta/proyecto && /ruta/venv/bin/python manage.py sincronizar_tasa_bcv >> logs/bcv_sync.log 2>&1
```

## Uso Manual

### Sincronizar Ahora

```bash
python manage.py sincronizar_tasa_bcv
```

**Salida esperada**:
```
Consultando tasa BCV...
[OK] Tasa obtenida: 45.50 BSD/USD
[OK] Tasa guardada en base de datos
```

### Modo Prueba

```bash
python manage.py sincronizar_tasa_bcv --dry-run
```

**Salida esperada**:
```
Consultando tasa BCV...
[OK] Tasa obtenida: 45.50 BSD/USD
[DRY-RUN] No se guardó en base de datos
```

## Integración con Código

### Uso Directo del Cliente

```python
from contabilidad.bcv_client import BCVClient

# Obtener tasa actual
tasa = BCVClient.obtener_tasa_actual()
if tasa:
    print(f"Tasa BCV: {tasa} BSD/USD")

# Actualizar en DB
if BCVClient.actualizar_tasa_db():
    print("Tasa actualizada correctamente")
```

### Fallback Automático

El servicio `ContabilidadService.obtener_tasa_bcv()` ya implementa fallback:
1. Busca tasa para fecha específica
2. Si no existe, busca la más reciente
3. Si no hay ninguna, lanza error

Con sincronización automática, siempre habrá tasa reciente disponible.

## Logs

Los logs se guardan en `logs/bcv_sync.log`:

```
2025-01-15 09:00:01 INFO: Tasa BCV obtenida: 45.50 BSD/USD
2025-01-15 09:00:02 INFO: Tasa BCV actualizada: 2025-01-15 = 45.50 BSD/USD
```

## Manejo de Errores

### Error de Conexión

```
[ERROR] No se pudo obtener la tasa del BCV
```

**Causas posibles**:
- Sin conexión a internet
- Sitio BCV caído
- Timeout (>10 segundos)

**Solución**: El sistema usará la tasa más reciente disponible en DB.

### Error de Parsing

```
ERROR: No se encontró div#dolar en página BCV
```

**Causa**: BCV cambió estructura de su sitio web.

**Solución**: Actualizar selectores en `bcv_client.py`.

## Monitoreo

### Verificar Última Sincronización

```python
from contabilidad.models import TasaCambioBCV

ultima = TasaCambioBCV.objects.order_by('-fecha').first()
print(f"Última tasa: {ultima.fecha} = {ultima.tasa_bsd_por_usd}")
print(f"Fuente: {ultima.fuente}")
```

### Dashboard Admin

En Admin → Contabilidad → Tasas de Cambio BCV:
- Ver historial completo
- Filtrar por fuente
- Verificar actualizaciones automáticas

## Ventajas

1. ✅ **Cero intervención manual**: Actualización diaria automática
2. ✅ **Siempre actualizado**: Tasa del día disponible
3. ✅ **Fallback robusto**: Usa última tasa si falla
4. ✅ **Trazabilidad**: Fuente registrada en cada tasa
5. ✅ **Logs completos**: Auditoría de sincronizaciones
6. ✅ **Modo prueba**: Validar sin guardar

## Troubleshooting

### Problema: Tarea no se ejecuta

**Verificar**:
1. Task Scheduler → Historial de tareas
2. Revisar `logs/bcv_sync.log`
3. Verificar permisos de ejecución

### Problema: Error de parsing

**Solución temporal**:
```bash
# Actualizar manualmente mientras se corrige
python manage.py actualizar_tasa_bcv --tasa 45.50
```

**Solución permanente**:
- Revisar estructura actual del sitio BCV
- Actualizar selectores en `bcv_client.py`

### Problema: Timeout constante

**Ajustar timeout**:
```python
# En bcv_client.py
TIMEOUT = 30  # Aumentar a 30 segundos
```

## Próximas Mejoras

1. **API oficial BCV** (si se publica)
2. **Múltiples fuentes** (fallback a otras fuentes)
3. **Notificaciones** si falla sincronización
4. **Dashboard** con gráfico de evolución
5. **Alertas** por cambios bruscos de tasa

## Soporte

- Cliente: `contabilidad/bcv_client.py`
- Comando: `contabilidad/management/commands/sincronizar_tasa_bcv.py`
- Script: `sincronizar_bcv.bat`
- Logs: `logs/bcv_sync.log`

---

**Estado**: ✅ Implementado y Funcional  
**Versión**: 1.0  
**Fecha**: Enero 2025
