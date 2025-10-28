# ✅ DolarApi Venezuela Integrado

## 🎉 Funcionando Perfectamente

La API de DolarApi Venezuela está integrada y funcionando correctamente.

### 📊 Tasas Actuales (18 Oct 2025)

- **BCV Oficial**: 205.68 Bs/USD
- **Paralelo**: 297.14 Bs/USD  
- **Bitcoin**: 115.17 Bs/USD

---

## 🔧 Sincronización

### Manual
```bash
python manage.py sincronizar_tasa_bcv
```

### Ver Todas las Tasas
```bash
python manage.py sincronizar_tasa_bcv --todas
```

**Salida**:
```
============================================================
  SINCRONIZACIÓN DE TASAS DE CAMBIO - VENEZUELA
============================================================
Fecha/Hora: 2025-10-18 17:05:06

Consultando tasas...

[OK] 3 tasas obtenidas
  BCV OFICIAL:      205.68 Bs/USD
  PARALELO:         297.14 Bs/USD
  BITCOIN:          115.17 Bs/USD

Guardando en base de datos...
[OK] Tasa BCV guardada correctamente

============================================================
Sincronización completada
============================================================
```

---

## 🤖 Automatización

### Configurar Tareas Programadas

**Ejecutar como Administrador**:
```cmd
cd C:\Users\ARMANDO\travelhub_project\batch_scripts
configurar_tareas_programadas.bat
```

Esto creará 3 tareas que sincronizarán automáticamente:
- **08:00 AM** - Sincronización matutina
- **12:00 PM** - Sincronización mediodía
- **05:00 PM** - Sincronización tarde

---

## 🌐 API Endpoints

### 1. Solo BCV Oficial
```
GET http://127.0.0.1:8000/api/contabilidad/api/tasas/bcv/
```

**Respuesta**:
```json
{
  "valor": 205.68,
  "fecha": "2025-10-18"
}
```

### 2. Todas las Tasas
```
GET http://127.0.0.1:8000/api/contabilidad/api/tasas/actuales/
```

**Respuesta**:
```json
{
  "oficial": {
    "valor": 205.68,
    "fecha": "2025-10-18T18:04:40.920Z",
    "nombre": "BCV Oficial"
  },
  "paralelo": {
    "valor": 297.14,
    "fecha": "2025-10-18T18:04:44.591Z",
    "nombre": "Paralelo"
  },
  "bitcoin": {
    "valor": 115.17,
    "fecha": "2025-10-18T18:04:40.920Z",
    "nombre": "Bitcoin"
  }
}
```

---

## 💻 Integración Frontend

### Código React/Next.js

```javascript
// En tu componente Header
import { useEffect, useState } from 'react';

export default function Header() {
  const [tasaBCV, setTasaBCV] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchTasa = async () => {
      try {
        const response = await fetch('http://127.0.0.1:8000/api/contabilidad/api/tasas/bcv/');
        const data = await response.json();
        setTasaBCV(data.valor);
      } catch (error) {
        console.error('Error obteniendo tasa:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchTasa();

    // Actualizar cada 5 minutos
    const interval = setInterval(fetchTasa, 300000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="flex justify-between items-center p-4 bg-white shadow">
      {/* Lado izquierdo - Tasa BCV */}
      <div className="flex items-center gap-4">
        {loading ? (
          <div className="text-sm text-gray-500">Cargando...</div>
        ) : tasaBCV ? (
          <div className="flex items-center gap-1 text-sm">
            <span className="text-gray-600">USD:</span>
            <span className="font-semibold text-green-600">
              {tasaBCV.toFixed(2)}
            </span>
            <span className="text-gray-600">Bs</span>
          </div>
        ) : null}
        
        <div className="text-gray-300">|</div>
        
        <div className="text-gray-700">
          Bienvenido, <span className="font-medium">Armando3105</span>
        </div>
      </div>

      {/* Lado derecho - Menú usuario */}
      <div>
        {/* Tu menú actual */}
      </div>
    </header>
  );
}
```

---

## 📍 Ver en Django Admin

1. **Ir a**: http://127.0.0.1:8000/admin/contabilidad/tasacambiobcv/
2. **Verás**: La tasa de hoy (205.68 Bs/USD)
3. **Fuente**: DolarApi - BCV Oficial

---

## 🔍 Verificar Tasa Actual

```bash
python manage.py shell -c "from contabilidad.models import TasaCambioBCV; from datetime import date; t = TasaCambioBCV.objects.filter(fecha=date.today()).first(); print(f'Tasa: {t.tasa_bsd_por_usd} Bs/USD' if t else 'No hay tasa')"
```

**Salida**:
```
Tasa: 205.6800 Bs/USD
```

---

## 📚 Documentación API Externa

- **URL**: https://dolarapi.com/docs/venezuela/
- **Endpoint**: https://ve.dolarapi.com/v1/dolares
- **Tipo**: Gratuita y de código abierto
- **Actualización**: Tiempo real

---

## ✅ Características

- ✅ API gratuita y confiable
- ✅ 3 tasas disponibles (Oficial, Paralelo, Bitcoin)
- ✅ Actualización en tiempo real
- ✅ Sincronización automática 3x día
- ✅ Caché de 5 minutos en endpoints
- ✅ Fallback a base de datos si API falla
- ✅ Logs automáticos

---

## 🎯 Próximos Pasos

1. ✅ **Configurar tareas automáticas**:
   ```cmd
   batch_scripts\configurar_tareas_programadas.bat
   ```

2. ✅ **Integrar en frontend**:
   - Copiar código React de arriba
   - Agregar en componente Header
   - Mostrar al lado de "Bienvenido"

3. ✅ **Verificar funcionamiento**:
   - Esperar a las 08:00, 12:00 o 17:00
   - O ejecutar manualmente: `python manage.py sincronizar_tasa_bcv`
   - Revisar logs: `type logs\tasas_sync.log`

---

## 🆘 Troubleshooting

### Si no se actualiza la tasa

```bash
# Verificar conexión a API
curl https://ve.dolarapi.com/v1/dolares

# Sincronizar manualmente
python manage.py sincronizar_tasa_bcv

# Ver logs
type logs\tasas_sync.log
```

### Si el frontend no muestra la tasa

1. Verificar que el servidor Django esté corriendo
2. Verificar que la URL sea correcta: `http://127.0.0.1:8000/api/contabilidad/api/tasas/bcv/`
3. Verificar en consola del navegador (F12) si hay errores

---

**Estado**: ✅ Completamente funcional  
**API**: DolarApi Venezuela  
**Última sincronización**: 18 de Octubre de 2025, 17:05  
**Tasa actual**: 205.68 Bs/USD
