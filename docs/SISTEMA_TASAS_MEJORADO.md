# Sistema de Tasas de Cambio Mejorado - TravelHub

## Resumen

Sistema completo para obtener y mostrar tasas de cambio de Venezuela:
- **BCV Oficial** (Banco Central de Venezuela)
- **Promedio** (mercado)
- **P2P** (Binance, Reserve, etc.)
- **Sincronización automática** 3 veces al día
- **API pública** para frontend
- **Caché** de 5 minutos

---

## Componentes Nuevos

### 1. Cliente de Tasas (`tasas_venezuela_client.py`)
**Ubicación**: `contabilidad/tasas_venezuela_client.py`

**Funciones principales**:
- `obtener_todas_tasas()` - Todas las tasas disponibles
- `obtener_tasa_bcv()` - Solo BCV oficial
- `obtener_tasa_promedio()` - Tasa promedio del mercado
- `obtener_tasa_p2p()` - Tasa P2P (Binance)
- `actualizar_tasas_db()` - Guarda en base de datos
- `obtener_resumen_tasas()` - Resumen para frontend

**API Externa**: https://pydolarve.org/api/v1/dollar

### 2. Endpoints API (`views_tasas.py`)
**Ubicación**: `contabilidad/views_tasas.py`

**Endpoints**:

#### GET /api/contabilidad/tasas/actuales/
Obtiene todas las tasas (BCV, Promedio, P2P)
```json
{
  "bcv": {
    "valor": 36.50,
    "fecha": "2025-01-20 14:30",
    "nombre": "BCV Oficial"
  },
  "promedio": {
    "valor": 37.20,
    "fecha": "2025-01-20 14:30",
    "nombre": "Promedio"
  },
  "p2p": {
    "valor": 37.50,
    "fecha": "2025-01-20 14:30",
    "nombre": "P2P (Binance)"
  }
}
```

#### GET /api/contabilidad/tasas/bcv/
Obtiene solo BCV (simplificado para header)
```json
{
  "valor": 36.50,
  "fecha": "2025-01-20"
}
```

#### POST /api/contabilidad/tasas/sincronizar/
Sincroniza manualmente (requiere autenticación)

### 3. Comando Mejorado
**Ubicación**: `contabilidad/management/commands/sincronizar_tasa_bcv.py`

**Uso**:
```bash
# Sincronización normal
python manage.py sincronizar_tasa_bcv

# Ver todas las tasas disponibles
python manage.py sincronizar_tasa_bcv --todas

# Modo prueba (no guarda)
python manage.py sincronizar_tasa_bcv --dry-run
```

**Salida**:
```
============================================================
  SINCRONIZACIÓN DE TASAS DE CAMBIO - VENEZUELA
============================================================
Fecha/Hora: 2025-01-20 14:30:00

Consultando tasas...

[OK] 15 tasas obtenidas

  BCV OFICIAL:       36.50 Bs/USD
  PROMEDIO:          37.20 Bs/USD
  P2P (Binance):     37.50 Bs/USD

Guardando en base de datos...
[OK] Tasa BCV guardada correctamente

============================================================
Sincronización completada
============================================================
```

### 4. Scripts de Automatización

#### `sincronizar_tasas_auto.bat`
Script que ejecuta la sincronización y guarda logs.

#### `configurar_tareas_programadas.bat`
Configura 3 tareas en Windows Task Scheduler:
- **08:00 AM** - Sincronización matutina
- **12:00 PM** - Sincronización mediodía
- **05:00 PM** - Sincronización tarde

---

## Instalación y Configuración

### Paso 1: Instalar Dependencia
```bash
pip install requests beautifulsoup4
```

### Paso 2: Probar Manualmente
```bash
python manage.py sincronizar_tasa_bcv --todas
```

### Paso 3: Configurar Tareas Automáticas
**Ejecutar como Administrador**:
```cmd
cd C:\Users\ARMANDO\travelhub_project\batch_scripts
configurar_tareas_programadas.bat
```

Esto creará 3 tareas programadas que se ejecutarán automáticamente.

### Paso 4: Verificar Tareas
```cmd
# Ver tareas creadas
schtasks /Query /TN "TravelHub_Tasas_08AM"
schtasks /Query /TN "TravelHub_Tasas_12PM"
schtasks /Query /TN "TravelHub_Tasas_05PM"

# Ejecutar manualmente
schtasks /Run /TN "TravelHub_Tasas_08AM"

# Ver logs
type logs\tasas_sync.log
```

---

## Integración con Frontend

### Opción 1: Mostrar Solo BCV (Recomendado)
```javascript
// En el header del frontend
useEffect(() => {
  fetch('http://localhost:8000/api/contabilidad/tasas/bcv/')
    .then(res => res.json())
    .then(data => {
      setTasaBCV(data.valor);
    });
}, []);

// Mostrar en header
<div className="tasa-bcv">
  USD: {tasaBCV.toFixed(2)} Bs
</div>
```

### Opción 2: Mostrar Todas las Tasas
```javascript
// Obtener todas las tasas
useEffect(() => {
  fetch('http://localhost:8000/api/contabilidad/tasas/actuales/')
    .then(res => res.json())
    .then(data => {
      setTasas(data);
    });
}, []);

// Mostrar en dropdown o tooltip
<div className="tasas-dropdown">
  <div>BCV: {tasas.bcv?.valor.toFixed(2)} Bs</div>
  <div>Promedio: {tasas.promedio?.valor.toFixed(2)} Bs</div>
  <div>P2P: {tasas.p2p?.valor.toFixed(2)} Bs</div>
</div>
```

### Ubicación Sugerida en Frontend
**Lado izquierdo del header**, junto a "Bienvenido, usuario":

```
┌─────────────────────────────────────────────────┐
│ USD: 36.50 Bs  |  Bienvenido, Armando3105  [▼] │
└─────────────────────────────────────────────────┘
```

---

## Características

### ✅ Múltiples Fuentes
- BCV Oficial
- Promedio del mercado
- P2P (Binance, Reserve)
- Otras plataformas (PayPal, Zelle, etc.)

### ✅ Sincronización Automática
- 3 veces al día (08:00, 12:00, 17:00)
- Logs automáticos
- Manejo de errores

### ✅ Caché Inteligente
- 5 minutos de caché
- Reduce carga en API externa
- Fallback a base de datos

### ✅ API Pública
- Sin autenticación para lectura
- Formato JSON simple
- Compatible con cualquier frontend

### ✅ Fallback Robusto
1. Intenta API externa
2. Si falla, usa base de datos
3. Si no hay datos, retorna error claro

---

## Logs

**Ubicación**: `logs/tasas_sync.log`

**Formato**:
```
[20/01/2025 08:00:15] Sincronizando tasas de cambio...
[20/01/2025 08:00:17] Sincronizacion exitosa
[20/01/2025 12:00:10] Sincronizando tasas de cambio...
[20/01/2025 12:00:12] Sincronizacion exitosa
```

---

## Mantenimiento

### Ver Tasas Actuales
```bash
python manage.py sincronizar_tasa_bcv --todas
```

### Sincronizar Manualmente
```bash
python manage.py sincronizar_tasa_bcv
```

### Desactivar Tareas Automáticas
```cmd
schtasks /Delete /TN "TravelHub_Tasas_08AM" /F
schtasks /Delete /TN "TravelHub_Tasas_12PM" /F
schtasks /Delete /TN "TravelHub_Tasas_05PM" /F
```

### Cambiar Horarios
Editar `configurar_tareas_programadas.bat` y cambiar `/ST 08:00` por el horario deseado.

---

## Próximos Pasos

1. ✅ **Probar sincronización manual**
   ```bash
   python manage.py sincronizar_tasa_bcv --todas
   ```

2. ✅ **Configurar tareas automáticas**
   ```cmd
   configurar_tareas_programadas.bat
   ```

3. ✅ **Integrar en frontend**
   - Agregar componente en header
   - Mostrar tasa BCV al lado de "Bienvenido"

4. ⏳ **Opcional: Agregar más monedas**
   - EUR (Euro)
   - COP (Peso colombiano)
   - Otras según necesidad

---

## Soporte

**API Externa**: https://pydolarve.org/  
**Documentación API**: https://pydolarve.org/api/v1/dollar

**Logs**: `logs/tasas_sync.log`  
**Configuración**: `.env` (no requiere cambios)

---

**Fecha de implementación**: 20 de Enero de 2025  
**Estado**: ✅ Listo para usar
