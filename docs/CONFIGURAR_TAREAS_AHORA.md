# Configurar Tareas Automáticas - AHORA

## 🚀 Pasos Rápidos

### 1. Abrir PowerShell como Administrador

**Opción A**: Buscar "PowerShell" → Click derecho → "Ejecutar como administrador"

**Opción B**: Presionar `Win + X` → Seleccionar "Windows PowerShell (Administrador)"

### 2. Ejecutar el Script

```powershell
cd C:\Users\ARMANDO\travelhub_project\batch_scripts
.\configurar_tareas_programadas.bat
```

### 3. Verificar que se Crearon

```powershell
schtasks /Query /TN "TravelHub_Tasas_08AM"
schtasks /Query /TN "TravelHub_Tasas_12PM"
schtasks /Query /TN "TravelHub_Tasas_05PM"
```

### 4. Probar Manualmente

```powershell
schtasks /Run /TN "TravelHub_Tasas_08AM"
```

---

## ✅ Resultado Esperado

```
============================================
  CONFIGURACION DE TAREAS PROGRAMADAS
============================================

Proyecto: C:\Users\ARMANDO\travelhub_project
Script: C:\Users\ARMANDO\travelhub_project\batch_scripts\sincronizar_tasas_auto.bat

Eliminando tareas antiguas...

Creando tarea para las 08:00 AM...
[OK] Tarea 08:00 AM creada

Creando tarea para las 12:00 PM...
[OK] Tarea 12:00 PM creada

Creando tarea para las 05:00 PM...
[OK] Tarea 05:00 PM creada

============================================
  CONFIGURACION COMPLETADA
============================================

Tareas programadas creadas:
  - TravelHub_Tasas_08AM (08:00 AM diario)
  - TravelHub_Tasas_12PM (12:00 PM diario)
  - TravelHub_Tasas_05PM (05:00 PM diario)
```

---

## 📊 Tasas que se Sincronizarán

- **BCV Oficial**: 205.68 Bs/USD
- **Dólar No Oficial**: 297.14 Bs/USD
- **Bitcoin**: 115.17 Bs/USD

---

## 🌐 API para Frontend

### Endpoint: Ambas Tasas
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
    "nombre": "Dólar No Oficial"
  }
}
```

---

## 💻 Código Frontend (Ambas Tasas)

```javascript
// En tu componente Header
import { useEffect, useState } from 'react';

export default function Header() {
  const [tasas, setTasas] = useState(null);

  useEffect(() => {
    const fetchTasas = async () => {
      try {
        const response = await fetch('http://127.0.0.1:8000/api/contabilidad/api/tasas/actuales/');
        const data = await response.json();
        setTasas(data);
      } catch (error) {
        console.error('Error:', error);
      }
    };

    fetchTasas();
    const interval = setInterval(fetchTasas, 300000); // 5 min
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="flex justify-between items-center p-4 bg-white shadow">
      {/* Lado izquierdo - Tasas */}
      <div className="flex items-center gap-4">
        {tasas && (
          <>
            {/* BCV Oficial */}
            <div className="flex items-center gap-1 text-sm">
              <span className="text-gray-600">Oficial:</span>
              <span className="font-semibold text-green-600">
                {tasas.oficial?.valor.toFixed(2)}
              </span>
              <span className="text-gray-600">Bs</span>
            </div>
            
            <div className="text-gray-300">|</div>
            
            {/* Dólar No Oficial */}
            <div className="flex items-center gap-1 text-sm">
              <span className="text-gray-600">No Oficial:</span>
              <span className="font-semibold text-blue-600">
                {tasas.paralelo?.valor.toFixed(2)}
              </span>
              <span className="text-gray-600">Bs</span>
            </div>
          </>
        )}
        
        <div className="text-gray-300">|</div>
        
        <div className="text-gray-700">
          Bienvenido, <span className="font-medium">Armando3105</span>
        </div>
      </div>

      {/* Lado derecho - Menú */}
      <div>
        {/* Tu menú actual */}
      </div>
    </header>
  );
}
```

---

## 🎨 Diseño Sugerido

```
┌────────────────────────────────────────────────────────────┐
│  Oficial: 205.68 Bs | No Oficial: 297.14 Bs | Bienvenido  │
└────────────────────────────────────────────────────────────┘
```

---

## 📝 Logs

Ver logs de sincronización:
```powershell
type C:\Users\ARMANDO\travelhub_project\logs\tasas_sync.log
```

---

**IMPORTANTE**: Debes ejecutar el script como Administrador para que funcione.
