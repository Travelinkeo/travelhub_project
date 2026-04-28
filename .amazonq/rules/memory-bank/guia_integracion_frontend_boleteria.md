# Guía de Integración Frontend - Sistema de Boletería

**Fecha**: 25 de Enero de 2025  
**Para**: Next.js 14 + TypeScript

---

## 📋 Endpoints API Disponibles

### Base URL
```
http://localhost:8000/api/
```

### Autenticación
Todos los endpoints requieren JWT token:
```typescript
headers: {
  'Authorization': `Bearer ${accessToken}`,
  'Content-Type': 'application/json'
}
```

---

## 🎯 Endpoints por Funcionalidad

### 1. Notificaciones Proactivas
**Automático** - Se ejecuta en el backend cuando se procesa un boleto.

### 2. Validación de Boletos

```typescript
// POST /api/boletos-importados/{id}/validar/
const validarBoleto = async (boletoId: number) => {
  const response = await fetch(`/api/boletos-importados/${boletoId}/validar/`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json'
    }
  });
  
  const resultado = await response.json();
  // {
  //   valido: boolean,
  //   errores: string[],
  //   advertencias: string[]
  // }
  
  return resultado;
};
```

### 3. Reportes de Comisiones

```typescript
// GET /api/boletos-importados/reporte_comisiones/
const obtenerReporteComisiones = async (
  fechaInicio?: string,
  fechaFin?: string
) => {
  const params = new URLSearchParams();
  if (fechaInicio) params.append('fecha_inicio', fechaInicio);
  if (fechaFin) params.append('fecha_fin', fechaFin);
  
  const response = await fetch(
    `/api/boletos-importados/reporte_comisiones/?${params}`,
    {
      headers: {
        'Authorization': `Bearer ${accessToken}`
      }
    }
  );
  
  return await response.json();
  // {
  //   periodo: { fecha_inicio, fecha_fin },
  //   por_aerolinea: [...],
  //   totales: { total_boletos, total_ventas, total_comisiones }
  // }
};
```

### 4. Dashboard en Tiempo Real

```typescript
// GET /api/boletos-importados/dashboard/
const obtenerMetricasDashboard = async () => {
  const response = await fetch('/api/boletos-importados/dashboard/', {
    headers: {
      'Authorization': `Bearer ${accessToken}`
    }
  });
  
  return await response.json();
  // {
  //   procesados: { hoy, semana, mes },
  //   tasas_exito_gds: [...],
  //   pendientes: number,
  //   errores: number,
  //   top_aerolineas: [...]
  // }
};
```

### 5. Búsqueda Inteligente

```typescript
// GET /api/boletos-importados/busqueda_avanzada/
const buscarBoletos = async (filtros: {
  nombre?: string;
  fecha_inicio?: string;
  fecha_fin?: string;
  origen?: string;
  destino?: string;
  aerolinea?: string;
  estado?: string;
  pnr?: string;
}) => {
  const params = new URLSearchParams();
  Object.entries(filtros).forEach(([key, value]) => {
    if (value) params.append(key, value);
  });
  
  const response = await fetch(
    `/api/boletos-importados/busqueda_avanzada/?${params}`,
    {
      headers: {
        'Authorization': `Bearer ${accessToken}`
      }
    }
  );
  
  return await response.json();
};
```

### 6. Historial de Cambios

```typescript
// GET /api/historial-cambios-boletos/
const obtenerHistorialBoleto = async (boletoId: number) => {
  const response = await fetch(
    `/api/historial-cambios-boletos/?boleto=${boletoId}`,
    {
      headers: {
        'Authorization': `Bearer ${accessToken}`
      }
    }
  );
  
  return await response.json();
};

// POST /api/historial-cambios-boletos/
const registrarCambio = async (cambio: {
  boleto: number;
  tipo_cambio: 'CF' | 'CP' | 'RE' | 'CA' | 'CO' | 'OT';
  descripcion: string;
  datos_anteriores?: any;
  datos_nuevos?: any;
  costo_cambio?: number;
  penalidad?: number;
}) => {
  const response = await fetch('/api/historial-cambios-boletos/', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(cambio)
  });
  
  return await response.json();
};
```

### 7. Anulaciones/Reembolsos

```typescript
// POST /api/anulaciones-boletos/
const solicitarAnulacion = async (anulacion: {
  boleto: number;
  tipo_anulacion: 'VOL' | 'INV' | 'CAM';
  motivo: string;
  monto_original: number;
  penalidad_aerolinea: number;
  fee_agencia: number;
}) => {
  const response = await fetch('/api/anulaciones-boletos/', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(anulacion)
  });
  
  return await response.json();
};

// POST /api/anulaciones-boletos/{id}/aprobar/
const aprobarAnulacion = async (anulacionId: number) => {
  const response = await fetch(
    `/api/anulaciones-boletos/${anulacionId}/aprobar/`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${accessToken}`
      }
    }
  );
  
  return await response.json();
};

// POST /api/anulaciones-boletos/{id}/rechazar/
const rechazarAnulacion = async (
  anulacionId: number,
  motivoRechazo: string
) => {
  const response = await fetch(
    `/api/anulaciones-boletos/${anulacionId}/rechazar/`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ motivo_rechazo: motivoRechazo })
    }
  );
  
  return await response.json();
};

// POST /api/anulaciones-boletos/{id}/marcar_reembolsada/
const marcarReembolsada = async (anulacionId: number) => {
  const response = await fetch(
    `/api/anulaciones-boletos/${anulacionId}/marcar_reembolsada/`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${accessToken}`
      }
    }
  );
  
  return await response.json();
};
```

---

## 🎨 Componentes de Ejemplo

### Dashboard de Boletos

```typescript
// app/boletos/dashboard/page.tsx
'use client';

import { useEffect, useState } from 'react';

export default function DashboardBoletos() {
  const [metricas, setMetricas] = useState(null);
  
  useEffect(() => {
    const cargarMetricas = async () => {
      const data = await obtenerMetricasDashboard();
      setMetricas(data);
    };
    
    cargarMetricas();
    // Actualizar cada 30 segundos
    const interval = setInterval(cargarMetricas, 30000);
    return () => clearInterval(interval);
  }, []);
  
  if (!metricas) return <div>Cargando...</div>;
  
  return (
    <div className="grid grid-cols-3 gap-4">
      <div className="card">
        <h3>Procesados Hoy</h3>
        <p className="text-3xl">{metricas.procesados.hoy}</p>
      </div>
      
      <div className="card">
        <h3>Esta Semana</h3>
        <p className="text-3xl">{metricas.procesados.semana}</p>
      </div>
      
      <div className="card">
        <h3>Este Mes</h3>
        <p className="text-3xl">{metricas.procesados.mes}</p>
      </div>
      
      <div className="card col-span-3">
        <h3>Top Aerolíneas</h3>
        <ul>
          {metricas.top_aerolineas.map(a => (
            <li key={a.aerolinea_emisora}>
              {a.aerolinea_emisora}: {a.cantidad} boletos
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
```

### Validador de Boletos

```typescript
// components/ValidadorBoleto.tsx
'use client';

import { useState } from 'react';

export default function ValidadorBoleto({ boletoId }: { boletoId: number }) {
  const [resultado, setResultado] = useState(null);
  const [loading, setLoading] = useState(false);
  
  const validar = async () => {
    setLoading(true);
    const data = await validarBoleto(boletoId);
    setResultado(data);
    setLoading(false);
  };
  
  return (
    <div>
      <button onClick={validar} disabled={loading}>
        {loading ? 'Validando...' : 'Validar Boleto'}
      </button>
      
      {resultado && (
        <div className="mt-4">
          {resultado.valido ? (
            <div className="alert alert-success">
              ✅ Boleto válido
            </div>
          ) : (
            <div className="alert alert-error">
              ❌ Errores encontrados:
              <ul>
                {resultado.errores.map((e, i) => (
                  <li key={i}>{e}</li>
                ))}
              </ul>
            </div>
          )}
          
          {resultado.advertencias.length > 0 && (
            <div className="alert alert-warning">
              ⚠️ Advertencias:
              <ul>
                {resultado.advertencias.map((a, i) => (
                  <li key={i}>{a}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
```

### Buscador de Boletos

```typescript
// app/boletos/buscar/page.tsx
'use client';

import { useState } from 'react';

export default function BuscadorBoletos() {
  const [filtros, setFiltros] = useState({
    nombre: '',
    fecha_inicio: '',
    fecha_fin: '',
    origen: '',
    destino: '',
    aerolinea: '',
    estado: '',
    pnr: ''
  });
  const [resultados, setResultados] = useState([]);
  
  const buscar = async () => {
    const data = await buscarBoletos(filtros);
    setResultados(data);
  };
  
  return (
    <div>
      <div className="grid grid-cols-2 gap-4 mb-4">
        <input
          placeholder="Nombre pasajero"
          value={filtros.nombre}
          onChange={e => setFiltros({...filtros, nombre: e.target.value})}
        />
        
        <input
          type="date"
          placeholder="Fecha inicio"
          value={filtros.fecha_inicio}
          onChange={e => setFiltros({...filtros, fecha_inicio: e.target.value})}
        />
        
        <input
          placeholder="Origen (CCS)"
          value={filtros.origen}
          onChange={e => setFiltros({...filtros, origen: e.target.value})}
        />
        
        <input
          placeholder="Destino (MIA)"
          value={filtros.destino}
          onChange={e => setFiltros({...filtros, destino: e.target.value})}
        />
        
        <button onClick={buscar} className="col-span-2">
          Buscar
        </button>
      </div>
      
      <div>
        {resultados.map(boleto => (
          <div key={boleto.id_boleto_importado} className="card">
            <h3>{boleto.numero_boleto}</h3>
            <p>{boleto.nombre_pasajero_procesado}</p>
            <p>{boleto.aerolinea_emisora}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
```

---

## 📊 Tipos TypeScript

```typescript
// types/boletos.ts

export interface Boleto {
  id_boleto_importado: number;
  numero_boleto: string;
  nombre_pasajero_procesado: string;
  aerolinea_emisora: string;
  fecha_emision_boleto: string;
  total_boleto: number;
  estado_parseo: 'PEN' | 'PRO' | 'COM' | 'ERR' | 'NAP';
}

export interface ResultadoValidacion {
  valido: boolean;
  errores: string[];
  advertencias: string[];
}

export interface MetricasDashboard {
  procesados: {
    hoy: number;
    semana: number;
    mes: number;
  };
  tasas_exito_gds: Array<{
    formato_detectado: string;
    total: number;
    exitosos: number;
    tasa_exito: number;
  }>;
  pendientes: number;
  errores: number;
  top_aerolineas: Array<{
    aerolinea_emisora: string;
    cantidad: number;
  }>;
}

export interface HistorialCambio {
  id_historial: number;
  boleto: number;
  tipo_cambio: 'CF' | 'CP' | 'RE' | 'CA' | 'CO' | 'OT';
  descripcion: string;
  datos_anteriores: any;
  datos_nuevos: any;
  costo_cambio: number;
  penalidad: number;
  fecha_cambio: string;
}

export interface Anulacion {
  id_anulacion: number;
  boleto: number;
  tipo_anulacion: 'VOL' | 'INV' | 'CAM';
  estado: 'SOL' | 'PRO' | 'APR' | 'REC' | 'REE';
  motivo: string;
  monto_original: number;
  penalidad_aerolinea: number;
  fee_agencia: number;
  monto_reembolso: number;
  fecha_solicitud: string;
}
```

---

## ✅ Checklist de Integración

### Backend
- [x] ViewSets creados
- [x] Endpoints registrados
- [x] Migraciones aplicadas
- [x] Autenticación JWT configurada

### Frontend
- [ ] Crear página de dashboard
- [ ] Crear componente de validación
- [ ] Crear buscador avanzado
- [ ] Crear formulario de anulaciones
- [ ] Crear vista de historial
- [ ] Agregar tipos TypeScript
- [ ] Implementar manejo de errores
- [ ] Agregar loading states

---

**Última actualización**: 25 de Enero de 2025  
**Estado**: Backend completo, frontend pendiente  
**Autor**: Amazon Q Developer
