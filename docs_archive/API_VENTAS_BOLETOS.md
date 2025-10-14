# API de Ventas de Boletos para Frontend

## Endpoints

### 1. Obtener Ventas de Boletos

**URL**: `GET /api/ventas-boletos/`

**Parámetros Query**:
- `localizador` (opcional): Filtrar por localizador
- `fecha_desde` (opcional): Fecha desde (YYYY-MM-DD)
- `fecha_hasta` (opcional): Fecha hasta (YYYY-MM-DD)

**Respuesta**:
```json
{
  "ventas": [
    {
      "id": 1,
      "localizador": "ABC123",
      "fecha": "2025-01-15T10:30:00",
      "cliente": "Juan Pérez",
      "pasajeros": [
        {
          "id": 1,
          "apellidos": "Pérez",
          "nombres": "Juan",
          "tipo": "ADT",
          "documento": "V12345678"
        }
      ],
      "cantidad_boletos": 2,
      "aerolinea": "Avianca",
      "proveedores": ["Consolidador XYZ"],
      "total_venta": 1000.00,
      "costo_neto": 800.00,
      "fee_proveedor": 50.00,
      "comision": 100.00,
      "fee_agencia": 50.00,
      "margen": 200.00,
      "estado": "PEN",
      "estado_display": "Pendiente de Pago",
      "moneda": "USD",
      "items": [
        {
          "id": 1,
          "descripcion": "Boleto CCS-MIA",
          "precio": 500.00,
          "costo_neto": 400.00,
          "fee_proveedor": 25.00,
          "comision": 50.00,
          "fee_agencia": 25.00,
          "proveedor": "Consolidador XYZ"
        }
      ]
    }
  ],
  "stats": {
    "total_ventas": 10,
    "total_boletos": 25,
    "total_ingresos": 15000.00,
    "total_margen": 3000.00
  },
  "filtros": {
    "localizador": "",
    "fecha_desde": "",
    "fecha_hasta": ""
  }
}
```

### 2. Actualizar Item de Boleto

**URL**: `POST /api/boletos/actualizar-item/`

**Body**:
```json
{
  "item_id": 1,
  "campo": "costo_neto_proveedor",
  "valor": "450.00"
}
```

**Campos permitidos**:
- `costo_neto_proveedor`
- `fee_proveedor`
- `comision_agencia_monto`
- `fee_agencia_interno`

**Respuesta**:
```json
{
  "success": true,
  "nuevo_valor": 450.00,
  "total_venta": 1050.00,
  "margen": 150.00
}
```

## Integración Next.js

### Ejemplo de Uso

```typescript
// lib/api/ventas-boletos.ts
export async function getVentasBoletos(filtros?: {
  localizador?: string;
  fecha_desde?: string;
  fecha_hasta?: string;
}) {
  const params = new URLSearchParams();
  if (filtros?.localizador) params.append('localizador', filtros.localizador);
  if (filtros?.fecha_desde) params.append('fecha_desde', filtros.fecha_desde);
  if (filtros?.fecha_hasta) params.append('fecha_hasta', filtros.fecha_hasta);
  
  const response = await fetch(
    `http://127.0.0.1:8000/api/ventas-boletos/?${params}`
  );
  return response.json();
}

export async function actualizarItemBoleto(
  itemId: number,
  campo: string,
  valor: number
) {
  const response = await fetch(
    'http://127.0.0.1:8000/api/boletos/actualizar-item/',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ item_id: itemId, campo, valor })
    }
  );
  return response.json();
}
```

### Componente React

```typescript
// app/ventas-boletos/page.tsx
'use client';

import { useState, useEffect } from 'react';
import { getVentasBoletos, actualizarItemBoleto } from '@/lib/api/ventas-boletos';

export default function VentasBoletosPage() {
  const [ventas, setVentas] = useState([]);
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    loadVentas();
  }, []);
  
  async function loadVentas() {
    const data = await getVentasBoletos();
    setVentas(data.ventas);
    setStats(data.stats);
    setLoading(false);
  }
  
  async function handleEdit(itemId, campo, valor) {
    const result = await actualizarItemBoleto(itemId, campo, valor);
    if (result.success) {
      loadVentas(); // Recargar datos
    }
  }
  
  if (loading) return <div>Cargando...</div>;
  
  return (
    <div>
      <h1>Dashboard de Ventas de Boletos</h1>
      
      {/* Estadísticas */}
      <div className="stats-grid">
        <div>Total Ventas: {stats.total_ventas}</div>
        <div>Total Boletos: {stats.total_boletos}</div>
        <div>Ingresos: ${stats.total_ingresos}</div>
        <div>Margen: ${stats.total_margen}</div>
      </div>
      
      {/* Tabla de ventas */}
      <table>
        <thead>
          <tr>
            <th>Localizador</th>
            <th>Cliente</th>
            <th>Pasajeros</th>
            <th>Total</th>
            <th>Margen</th>
            <th>Estado</th>
          </tr>
        </thead>
        <tbody>
          {ventas.map(venta => (
            <tr key={venta.id}>
              <td>{venta.localizador}</td>
              <td>{venta.cliente}</td>
              <td>
                {venta.pasajeros.map(p => (
                  <div key={p.id}>
                    {p.apellidos}, {p.nombres} ({p.tipo})
                  </div>
                ))}
              </td>
              <td>{venta.moneda} {venta.total_venta}</td>
              <td>{venta.moneda} {venta.margen}</td>
              <td>{venta.estado_display}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

## Tipos TypeScript

```typescript
// types/ventas-boletos.ts
export interface Pasajero {
  id: number;
  apellidos: string;
  nombres: string;
  tipo: string;
  documento: string;
}

export interface ItemBoleto {
  id: number;
  descripcion: string;
  precio: number;
  costo_neto: number;
  fee_proveedor: number;
  comision: number;
  fee_agencia: number;
  proveedor: string | null;
}

export interface VentaBoleto {
  id: number;
  localizador: string;
  fecha: string;
  cliente: string;
  pasajeros: Pasajero[];
  cantidad_boletos: number;
  aerolinea: string;
  proveedores: string[];
  total_venta: number;
  costo_neto: number;
  fee_proveedor: number;
  comision: number;
  fee_agencia: number;
  margen: number;
  estado: string;
  estado_display: string;
  moneda: string;
  items: ItemBoleto[];
}

export interface VentasBoletosResponse {
  ventas: VentaBoleto[];
  stats: {
    total_ventas: number;
    total_boletos: number;
    total_ingresos: number;
    total_margen: number;
  };
  filtros: {
    localizador: string;
    fecha_desde: string;
    fecha_hasta: string;
  };
}
```

---

**Endpoints**:
- GET `/api/ventas-boletos/` - Obtener ventas
- POST `/api/boletos/actualizar-item/` - Actualizar item

**Estado**: ✅ Funcional
