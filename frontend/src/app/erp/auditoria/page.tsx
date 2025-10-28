'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import { TextField, Select, MenuItem, Chip, Button } from '@mui/material';

interface AuditLog {
  id: number;
  fecha: string;
  accion: string;
  modelo: string;
  descripcion: string;
  object_id: string;
  usuario?: string;
}

interface Estadisticas {
  por_accion: Array<{ accion: string; count: number }>;
  por_modelo: Array<{ modelo: string; count: number }>;
  total_registros: number;
}

export default function AuditoriaPage() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [estadisticas, setEstadisticas] = useState<Estadisticas | null>(null);
  const [filtroAccion, setFiltroAccion] = useState('');
  const [filtroModelo, setFiltroModelo] = useState('');
  const [search, setSearch] = useState('');
  const [ventaId, setVentaId] = useState('');
  const [timelineVenta, setTimelineVenta] = useState<any>(null);

  const cargarLogs = async () => {
    try {
      const params = new URLSearchParams();
      if (filtroAccion) params.append('accion', filtroAccion);
      if (filtroModelo) params.append('modelo', filtroModelo);
      if (search) params.append('search', search);
      
      const response = await api.get(`/api/audit-logs/?${params}`);
      setLogs(response.data.results || response.data);
    } catch (error) {
      console.error('Error cargando logs:', error);
    }
  };

  const cargarEstadisticas = async () => {
    try {
      const response = await api.get('/api/auditoria/estadisticas/');
      setEstadisticas(response.data);
    } catch (error) {
      console.error('Error cargando estadísticas:', error);
    }
  };

  const cargarTimelineVenta = async () => {
    if (!ventaId) return;
    try {
      const response = await api.get(`/api/auditoria/venta/${ventaId}/`);
      setTimelineVenta(response.data);
    } catch (error) {
      console.error('Error cargando timeline:', error);
      alert('Venta no encontrada');
    }
  };

  useEffect(() => {
    cargarLogs();
    cargarEstadisticas();
  }, [filtroAccion, filtroModelo, search]);

  const getAccionColor = (accion: string) => {
    switch (accion) {
      case 'CREATE': return 'success';
      case 'UPDATE': return 'info';
      case 'DELETE': return 'error';
      case 'STATE': return 'warning';
      default: return 'default';
    }
  };

  return (
    <div className="p-6">
      <h1 className="text-3xl font-bold mb-6">Auditoría y Trazabilidad</h1>

      {/* Estadísticas */}
      {estadisticas && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <div className="bg-white rounded-lg shadow p-4">
            <h3 className="font-bold text-lg mb-2">Total de Registros</h3>
            <p className="text-3xl font-bold text-blue-600">{estadisticas.total_registros}</p>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <h3 className="font-bold text-lg mb-2">Por Acción</h3>
            <div className="space-y-1">
              {estadisticas.por_accion.map((item) => (
                <div key={item.accion} className="flex justify-between">
                  <span>{item.accion}</span>
                  <span className="font-bold">{item.count}</span>
                </div>
              ))}
            </div>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <h3 className="font-bold text-lg mb-2">Por Modelo</h3>
            <div className="space-y-1">
              {estadisticas.por_modelo.slice(0, 5).map((item) => (
                <div key={item.modelo} className="flex justify-between">
                  <span>{item.modelo}</span>
                  <span className="font-bold">{item.count}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Timeline de Venta */}
      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <h3 className="font-bold text-lg mb-3">Timeline de Venta</h3>
        <div className="flex gap-2">
          <TextField
            label="ID de Venta"
            value={ventaId}
            onChange={(e) => setVentaId(e.target.value)}
            size="small"
            type="number"
          />
          <Button variant="contained" onClick={cargarTimelineVenta}>
            Buscar
          </Button>
        </div>
        {timelineVenta && (
          <div className="mt-4">
            <p className="text-sm text-gray-600 mb-2">
              Total de eventos: {timelineVenta.total_eventos}
            </p>
            <div className="space-y-2">
              {timelineVenta.timeline.map((evento: any) => (
                <div key={evento.id} className="border-l-4 border-blue-500 pl-4 py-2">
                  <div className="flex items-center gap-2 mb-1">
                    <Chip label={evento.accion} color={getAccionColor(evento.accion) as any} size="small" />
                    <span className="text-sm text-gray-600">
                      {new Date(evento.fecha).toLocaleString()}
                    </span>
                  </div>
                  <p className="text-sm">{evento.descripcion}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Filtros */}
      <div className="flex gap-4 mb-6">
        <TextField
          label="Buscar"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          size="small"
          className="flex-1"
        />
        <Select
          value={filtroAccion}
          onChange={(e) => setFiltroAccion(e.target.value)}
          displayEmpty
          size="small"
          className="w-48"
        >
          <MenuItem value="">Todas las acciones</MenuItem>
          <MenuItem value="CREATE">CREATE</MenuItem>
          <MenuItem value="UPDATE">UPDATE</MenuItem>
          <MenuItem value="DELETE">DELETE</MenuItem>
          <MenuItem value="STATE">STATE</MenuItem>
        </Select>
        <Select
          value={filtroModelo}
          onChange={(e) => setFiltroModelo(e.target.value)}
          displayEmpty
          size="small"
          className="w-48"
        >
          <MenuItem value="">Todos los modelos</MenuItem>
          <MenuItem value="Venta">Venta</MenuItem>
          <MenuItem value="ItemVenta">ItemVenta</MenuItem>
          <MenuItem value="Factura">Factura</MenuItem>
        </Select>
      </div>

      {/* Tabla de Logs */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Fecha</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Acción</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Modelo</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Object ID</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Descripción</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {logs.map((log) => (
              <tr key={log.id}>
                <td className="px-6 py-4 whitespace-nowrap text-sm">
                  {new Date(log.fecha).toLocaleString()}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <Chip label={log.accion} color={getAccionColor(log.accion) as any} size="small" />
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm">{log.modelo}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm">{log.object_id}</td>
                <td className="px-6 py-4 text-sm">{log.descripcion}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
