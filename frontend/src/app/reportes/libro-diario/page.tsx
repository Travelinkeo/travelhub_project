'use client';

import { useState } from 'react';
import { api } from '@/lib/api';
import { Button, TextField } from '@mui/material';

interface Asiento {
  numero_asiento: string;
  fecha: string;
  descripcion: string;
  total_debe: number;
  total_haber: number;
  esta_cuadrado: boolean;
  detalles: Array<{
    cuenta: string;
    cuenta_nombre: string;
    descripcion: string;
    debe: number;
    haber: number;
  }>;
}

export default function LibroDiarioPage() {
  const [fechaDesde, setFechaDesde] = useState('');
  const [fechaHasta, setFechaHasta] = useState('');
  const [asientos, setAsientos] = useState<Asiento[]>([]);
  const [loading, setLoading] = useState(false);

  const cargarLibroDiario = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (fechaDesde) params.append('fecha_desde', fechaDesde);
      if (fechaHasta) params.append('fecha_hasta', fechaHasta);
      
      const response = await api.get(`/api/reportes/libro-diario/?${params}`);
      setAsientos(response.data.asientos || []);
    } catch (error) {
      console.error('Error:', error);
      alert('Error al cargar libro diario');
    } finally {
      setLoading(false);
    }
  };

  const exportarExcel = async () => {
    try {
      const params = new URLSearchParams();
      if (fechaDesde) params.append('fecha_desde', fechaDesde);
      if (fechaHasta) params.append('fecha_hasta', fechaHasta);
      
      const response = await api.get(`/api/reportes/exportar-excel/?${params}`, {
        responseType: 'blob'
      });
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `libro_diario_${fechaDesde}_${fechaHasta}.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (error) {
      console.error('Error:', error);
      alert('Error al exportar');
    }
  };

  return (
    <div className="p-6">
      <h1 className="text-3xl font-bold mb-6">Libro Diario</h1>

      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <div className="flex gap-4 items-end">
          <TextField
            label="Fecha Desde"
            type="date"
            value={fechaDesde}
            onChange={(e) => setFechaDesde(e.target.value)}
            InputLabelProps={{ shrink: true }}
            size="small"
          />
          <TextField
            label="Fecha Hasta"
            type="date"
            value={fechaHasta}
            onChange={(e) => setFechaHasta(e.target.value)}
            InputLabelProps={{ shrink: true }}
            size="small"
          />
          <Button variant="contained" onClick={cargarLibroDiario} disabled={loading}>
            {loading ? 'Cargando...' : 'Consultar'}
          </Button>
          <Button variant="outlined" onClick={exportarExcel} disabled={!asientos.length}>
            Exportar Excel
          </Button>
        </div>
      </div>

      <div className="space-y-4">
        {asientos.map((asiento) => (
          <div key={asiento.numero_asiento} className="bg-white rounded-lg shadow overflow-hidden">
            <div className="bg-gray-50 px-6 py-3 border-b">
              <div className="flex justify-between items-center">
                <div>
                  <span className="font-bold">{asiento.numero_asiento}</span>
                  <span className="ml-4 text-gray-600">{asiento.fecha}</span>
                </div>
                <div className="text-right">
                  <span className={`font-bold ${asiento.esta_cuadrado ? 'text-green-600' : 'text-red-600'}`}>
                    {asiento.esta_cuadrado ? '✓ Cuadrado' : '✗ Descuadrado'}
                  </span>
                </div>
              </div>
              <p className="text-sm text-gray-600 mt-1">{asiento.descripcion}</p>
            </div>
            
            <table className="min-w-full">
              <thead className="bg-gray-100">
                <tr>
                  <th className="px-6 py-2 text-left text-xs font-medium text-gray-500">Cuenta</th>
                  <th className="px-6 py-2 text-left text-xs font-medium text-gray-500">Descripción</th>
                  <th className="px-6 py-2 text-right text-xs font-medium text-gray-500">Debe</th>
                  <th className="px-6 py-2 text-right text-xs font-medium text-gray-500">Haber</th>
                </tr>
              </thead>
              <tbody>
                {asiento.detalles.map((detalle, idx) => (
                  <tr key={idx} className="border-t">
                    <td className="px-6 py-2 text-sm">
                      {detalle.cuenta} - {detalle.cuenta_nombre}
                    </td>
                    <td className="px-6 py-2 text-sm">{detalle.descripcion}</td>
                    <td className="px-6 py-2 text-sm text-right">
                      {detalle.debe > 0 ? `$${detalle.debe.toFixed(2)}` : '-'}
                    </td>
                    <td className="px-6 py-2 text-sm text-right">
                      {detalle.haber > 0 ? `$${detalle.haber.toFixed(2)}` : '-'}
                    </td>
                  </tr>
                ))}
                <tr className="bg-gray-50 font-bold border-t-2">
                  <td colSpan={2} className="px-6 py-2 text-sm">TOTALES</td>
                  <td className="px-6 py-2 text-sm text-right">${asiento.total_debe.toFixed(2)}</td>
                  <td className="px-6 py-2 text-sm text-right">${asiento.total_haber.toFixed(2)}</td>
                </tr>
              </tbody>
            </table>
          </div>
        ))}
      </div>
    </div>
  );
}
