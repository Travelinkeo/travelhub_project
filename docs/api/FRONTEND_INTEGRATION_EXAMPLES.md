# Ejemplos de Integración Frontend - TravelHub API

Ejemplos prácticos de cómo consumir los endpoints desde React/Next.js.

## Configuración Inicial

```typescript
// lib/api-client.ts
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export class ApiClient {
  private token: string | null = null;

  setToken(token: string) {
    this.token = token;
    localStorage.setItem('access_token', token);
  }

  async request(endpoint: string, options: RequestInit = {}) {
    const headers = {
      'Content-Type': 'application/json',
      ...(this.token && { Authorization: `Bearer ${this.token}` }),
      ...options.headers,
    };

    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.statusText}`);
    }

    return response.json();
  }

  async get(endpoint: string) {
    return this.request(endpoint);
  }

  async post(endpoint: string, data: any) {
    return this.request(endpoint, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }
}

export const apiClient = new ApiClient();
```

## 1. Dashboard de Métricas

```typescript
// hooks/useDashboard.ts
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';

interface DashboardMetrics {
  resumen: {
    total_ventas: number;
    monto_total: number;
    saldo_pendiente: number;
    margen_estimado: number;
  };
  ventas_por_estado: Array<{
    estado: string;
    count: number;
    total: number;
  }>;
  top_clientes: Array<any>;
  tendencia_semanal: Array<any>;
}

export function useDashboard(fechaDesde?: string, fechaHasta?: string) {
  return useQuery({
    queryKey: ['dashboard', fechaDesde, fechaHasta],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (fechaDesde) params.append('fecha_desde', fechaDesde);
      if (fechaHasta) params.append('fecha_hasta', fechaHasta);
      
      return apiClient.get(`/api/dashboard/metricas/?${params}`) as Promise<DashboardMetrics>;
    },
  });
}

// Componente
export function DashboardPage() {
  const { data, isLoading } = useDashboard();

  if (isLoading) return <div>Cargando...</div>;

  return (
    <div className="grid grid-cols-4 gap-4">
      <MetricCard
        title="Total Ventas"
        value={data?.resumen.total_ventas}
        icon={<ShoppingCart />}
      />
      <MetricCard
        title="Monto Total"
        value={`$${data?.resumen.monto_total.toFixed(2)}`}
        icon={<DollarSign />}
      />
      <MetricCard
        title="Saldo Pendiente"
        value={`$${data?.resumen.saldo_pendiente.toFixed(2)}`}
        icon={<AlertCircle />}
      />
      <MetricCard
        title="Margen"
        value={`$${data?.resumen.margen_estimado.toFixed(2)}`}
        icon={<TrendingUp />}
      />
    </div>
  );
}
```

## 2. Liquidaciones a Proveedores

```typescript
// hooks/useLiquidaciones.ts
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';

export function useLiquidaciones(filters?: { estado?: string; proveedor?: number }) {
  return useQuery({
    queryKey: ['liquidaciones', filters],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (filters?.estado) params.append('estado', filters.estado);
      if (filters?.proveedor) params.append('proveedor', filters.proveedor.toString());
      
      return apiClient.get(`/api/liquidaciones/?${params}`);
    },
  });
}

export function useMarcarPagada() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (liquidacionId: number) => {
      return apiClient.post(`/api/liquidaciones/${liquidacionId}/marcar_pagada/`, {});
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['liquidaciones'] });
    },
  });
}

export function useRegistrarPagoParcial() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ id, monto }: { id: number; monto: number }) => {
      return apiClient.post(`/api/liquidaciones/${id}/registrar_pago_parcial/`, { monto });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['liquidaciones'] });
    },
  });
}

// Componente
export function LiquidacionesTable() {
  const { data, isLoading } = useLiquidaciones({ estado: 'PEN' });
  const marcarPagada = useMarcarPagada();

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>ID</TableHead>
          <TableHead>Proveedor</TableHead>
          <TableHead>Monto</TableHead>
          <TableHead>Saldo</TableHead>
          <TableHead>Acciones</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {data?.results.map((liq: any) => (
          <TableRow key={liq.id_liquidacion}>
            <TableCell>{liq.id_liquidacion}</TableCell>
            <TableCell>{liq.proveedor_detalle.nombre}</TableCell>
            <TableCell>${liq.monto_total}</TableCell>
            <TableCell>${liq.saldo_pendiente}</TableCell>
            <TableCell>
              <Button
                onClick={() => marcarPagada.mutate(liq.id_liquidacion)}
                disabled={marcarPagada.isPending}
              >
                Marcar Pagada
              </Button>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
```

## 3. Generación de Vouchers

```typescript
// hooks/useVoucher.ts
export function useGenerarVoucher() {
  return useMutation({
    mutationFn: async (ventaId: number) => {
      const response = await fetch(
        `${API_BASE_URL}/api/ventas/${ventaId}/generar-voucher/`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${localStorage.getItem('access_token')}`,
          },
        }
      );

      if (!response.ok) throw new Error('Error generando voucher');

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `voucher-${ventaId}.pdf`;
      a.click();
      window.URL.revokeObjectURL(url);
    },
  });
}

// Componente
export function VentaDetailActions({ ventaId }: { ventaId: number }) {
  const generarVoucher = useGenerarVoucher();

  return (
    <Button
      onClick={() => generarVoucher.mutate(ventaId)}
      disabled={generarVoucher.isPending}
    >
      {generarVoucher.isPending ? 'Generando...' : 'Descargar Voucher'}
    </Button>
  );
}
```

## 4. Auditoría de Venta

```typescript
// hooks/useAuditoria.ts
export function useHistorialVenta(ventaId: number) {
  return useQuery({
    queryKey: ['auditoria', ventaId],
    queryFn: () => apiClient.get(`/api/auditoria/venta/${ventaId}/`),
  });
}

// Componente Timeline
export function AuditoriaTimeline({ ventaId }: { ventaId: number }) {
  const { data, isLoading } = useHistorialVenta(ventaId);

  if (isLoading) return <Skeleton />;

  return (
    <div className="space-y-4">
      {data?.timeline.map((evento: any) => (
        <div key={evento.id} className="flex gap-4 border-l-2 pl-4">
          <div className="flex-shrink-0">
            <Badge variant={getBadgeVariant(evento.accion)}>
              {evento.accion}
            </Badge>
          </div>
          <div className="flex-1">
            <p className="font-medium">{evento.descripcion}</p>
            <p className="text-sm text-muted-foreground">
              {new Date(evento.fecha).toLocaleString()}
            </p>
          </div>
        </div>
      ))}
    </div>
  );
}
```

## 5. Gestión de Pasaportes

```typescript
// hooks/usePasaportes.ts
export function usePasaportesPendientes() {
  return useQuery({
    queryKey: ['pasaportes', 'pendientes'],
    queryFn: () => apiClient.get('/api/pasaportes/pendientes/'),
  });
}

export function useCrearClienteDesdePasaporte() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (pasaporteId: number) => {
      return apiClient.post(`/api/pasaportes/${pasaporteId}/crear_cliente/`, {});
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pasaportes'] });
      queryClient.invalidateQueries({ queryKey: ['clientes'] });
    },
  });
}

// Componente
export function PasaportesPendientes() {
  const { data } = usePasaportesPendientes();
  const crearCliente = useCrearClienteDesdePasaporte();

  return (
    <div className="grid gap-4">
      {data?.map((pasaporte: any) => (
        <Card key={pasaporte.id}>
          <CardHeader>
            <CardTitle>{pasaporte.nombre_completo}</CardTitle>
            <CardDescription>
              Pasaporte: {pasaporte.numero_pasaporte}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <Badge>Confianza: {(pasaporte.confianza_ocr * 100).toFixed(0)}%</Badge>
              <Badge variant="outline">{pasaporte.nacionalidad}</Badge>
            </div>
          </CardContent>
          <CardFooter>
            <Button
              onClick={() => crearCliente.mutate(pasaporte.id)}
              disabled={crearCliente.isPending}
            >
              Crear Cliente
            </Button>
          </CardFooter>
        </Card>
      ))}
    </div>
  );
}
```

## 6. Boletos sin Venta

```typescript
// hooks/useBoletos.ts
export function useBoletosSinVenta() {
  return useQuery({
    queryKey: ['boletos', 'sin-venta'],
    queryFn: () => apiClient.get('/api/boletos/sin-venta/'),
  });
}

export function useCrearVentaDesdeBoleto() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (boletoId: number) => {
      return apiClient.post(`/api/boletos/${boletoId}/crear-venta/`, {});
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['boletos'] });
      queryClient.invalidateQueries({ queryKey: ['ventas'] });
    },
  });
}

// Componente
export function BoletosSinVentaList() {
  const { data } = useBoletosSinVenta();
  const crearVenta = useCrearVentaDesdeBoleto();

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Número Boleto</TableHead>
          <TableHead>Pasajero</TableHead>
          <TableHead>Total</TableHead>
          <TableHead>Acciones</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {data?.map((boleto: any) => (
          <TableRow key={boleto.id_boleto_importado}>
            <TableCell>{boleto.numero_boleto}</TableCell>
            <TableCell>{boleto.nombre_pasajero_completo}</TableCell>
            <TableCell>${boleto.total_boleto}</TableCell>
            <TableCell>
              <Button
                size="sm"
                onClick={() => crearVenta.mutate(boleto.id_boleto_importado)}
              >
                Crear Venta
              </Button>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
```

## 7. Reportes Contables

```typescript
// hooks/useReportes.ts
export function useLibroDiario(fechaDesde?: string, fechaHasta?: string) {
  return useQuery({
    queryKey: ['reportes', 'libro-diario', fechaDesde, fechaHasta],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (fechaDesde) params.append('fecha_desde', fechaDesde);
      if (fechaHasta) params.append('fecha_hasta', fechaHasta);
      
      return apiClient.get(`/api/reportes/libro-diario/?${params}`);
    },
  });
}

export function useExportarExcel(fechaDesde?: string, fechaHasta?: string) {
  return useMutation({
    mutationFn: async () => {
      const params = new URLSearchParams();
      if (fechaDesde) params.append('fecha_desde', fechaDesde);
      if (fechaHasta) params.append('fecha_hasta', fechaHasta);
      
      const response = await fetch(
        `${API_BASE_URL}/api/reportes/exportar-excel/?${params}`,
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem('access_token')}`,
          },
        }
      );

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `libro_diario_${new Date().toISOString().split('T')[0]}.xlsx`;
      a.click();
    },
  });
}
```

## Manejo de Errores Global

```typescript
// lib/error-handler.ts
import { toast } from 'sonner';

export function handleApiError(error: any) {
  if (error.response?.status === 401) {
    toast.error('Sesión expirada. Por favor inicia sesión nuevamente.');
    window.location.href = '/login';
    return;
  }

  if (error.response?.status === 403) {
    toast.error('No tienes permisos para realizar esta acción.');
    return;
  }

  if (error.response?.status === 404) {
    toast.error('Recurso no encontrado.');
    return;
  }

  toast.error(error.message || 'Error inesperado. Intenta nuevamente.');
}

// Usar en React Query
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      onError: handleApiError,
    },
    mutations: {
      onError: handleApiError,
    },
  },
});
```

## Configuración de React Query

```typescript
// app/providers.tsx
'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { useState } from 'react';

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60 * 1000, // 1 minuto
            refetchOnWindowFocus: false,
          },
        },
      })
  );

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  );
}
```

---

## Testing

```typescript
// __tests__/api/dashboard.test.ts
import { renderHook, waitFor } from '@testing-library/react';
import { useDashboard } from '@/hooks/useDashboard';

describe('useDashboard', () => {
  it('fetches dashboard metrics', async () => {
    const { result } = renderHook(() => useDashboard());

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toHaveProperty('resumen');
    expect(result.current.data?.resumen).toHaveProperty('total_ventas');
  });
});
```

---

Estos ejemplos cubren los casos de uso más comunes. Para más detalles, consulta `FRONTEND_API_ENDPOINTS.md`.
