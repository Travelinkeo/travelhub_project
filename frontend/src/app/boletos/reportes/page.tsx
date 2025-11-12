'use client';

import { useState } from 'react';
import { obtenerReporteComisiones } from '@/lib/api/boletos';
import type { ReporteComisiones } from '@/types/boletos';

export default function ReportesComisiones() {
  const [fechaInicio, setFechaInicio] = useState('');
  const [fechaFin, setFechaFin] = useState('');
  const [reporte, setReporte] = useState<ReporteComisiones | null>(null);
  const [loading, setLoading] = useState(false);

  const generar = async () => {
    setLoading(true);
    try {
      const data = await obtenerReporteComisiones(fechaInicio, fechaFin);
      setReporte(data);
    } catch (error) {
      console.error('Error:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold mb-8">Reportes de Comisiones</h1>
      
      <div className="bg-white p-6 rounded-lg shadow mb-8">
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div>
            <label className="block text-sm mb-2">Fecha Inicio</label>
            <input
              type="date"
              className="border p-2 rounded w-full"
              value={fechaInicio}
              onChange={e => setFechaInicio(e.target.value)}
            />
          </div>
          
          <div>
            <label className="block text-sm mb-2">Fecha Fin</label>
            <input
              type="date"
              className="border p-2 rounded w-full"
              value={fechaFin}
              onChange={e => setFechaFin(e.target.value)}
            />
          </div>
        </div>
        
        <button
          onClick={generar}
          disabled={loading}
          className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700 disabled:bg-gray-400"
        >
          {loading ? 'Generando...' : 'Generar Reporte'}
        </button>
      </div>

      {reporte && (
        <>
          <div className="bg-white p-6 rounded-lg shadow mb-8">
            <h2 className="text-2xl font-bold mb-4">Totales</h2>
            <div className="grid grid-cols-3 gap-6">
              <div>
                <p className="text-gray-500 text-sm">Total Boletos</p>
                <p className="text-3xl font-bold">{reporte.totales.total_boletos}</p>
              </div>
              <div>
                <p className="text-gray-500 text-sm">Total Ventas</p>
                <p className="text-3xl font-bold text-green-600">${reporte.totales.total_ventas}</p>
              </div>
              <div>
                <p className="text-gray-500 text-sm">Total Comisiones</p>
                <p className="text-3xl font-bold text-blue-600">${reporte.totales.total_comisiones}</p>
              </div>
            </div>
          </div>

          <div className="bg-white p-6 rounded-lg shadow">
            <h2 className="text-2xl font-bold mb-4">Por Aerolínea</h2>
            <table className="w-full">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-2">Aerolínea</th>
                  <th className="text-right py-2">Boletos</th>
                  <th className="text-right py-2">Ventas</th>
                  <th className="text-right py-2">Comisiones</th>
                </tr>
              </thead>
              <tbody>
                {reporte.por_aerolinea.map((a, i) => (
                  <tr key={i} className="border-b">
                    <td className="py-2">{a.aerolinea}</td>
                    <td className="text-right">{a.cantidad_boletos}</td>
                    <td className="text-right">${a.total_ventas}</td>
                    <td className="text-right font-bold text-blue-600">${a.total_comisiones}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
