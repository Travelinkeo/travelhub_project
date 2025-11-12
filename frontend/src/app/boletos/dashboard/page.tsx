'use client';

import { useEffect, useState } from 'react';
import { obtenerDashboard } from '@/lib/api/boletos';
import type { MetricasDashboard } from '@/types/boletos';

export default function DashboardBoletos() {
  const [metricas, setMetricas] = useState<MetricasDashboard | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const cargar = async () => {
      try {
        const data = await obtenerDashboard();
        setMetricas(data);
      } catch (error) {
        console.error('Error:', error);
      } finally {
        setLoading(false);
      }
    };
    
    cargar();
    const interval = setInterval(cargar, 30000); // Actualizar cada 30s
    return () => clearInterval(interval);
  }, []);

  if (loading) return <div className="p-8">Cargando...</div>;
  if (!metricas) return <div className="p-8">Error al cargar datos</div>;

  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold mb-8">Dashboard de Boletos</h1>
      
      <div className="grid grid-cols-3 gap-6 mb-8">
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-gray-500 text-sm mb-2">Procesados Hoy</h3>
          <p className="text-4xl font-bold text-blue-600">{metricas.procesados.hoy}</p>
        </div>
        
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-gray-500 text-sm mb-2">Esta Semana</h3>
          <p className="text-4xl font-bold text-green-600">{metricas.procesados.semana}</p>
        </div>
        
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-gray-500 text-sm mb-2">Este Mes</h3>
          <p className="text-4xl font-bold text-purple-600">{metricas.procesados.mes}</p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-xl font-bold mb-4">Top Aerolíneas</h3>
          <ul className="space-y-2">
            {metricas.top_aerolineas.map((a, i) => (
              <li key={i} className="flex justify-between">
                <span>{a.aerolinea_emisora}</span>
                <span className="font-bold">{a.cantidad}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-xl font-bold mb-4">Estado</h3>
          <div className="space-y-4">
            <div className="flex justify-between">
              <span>Pendientes:</span>
              <span className="font-bold text-yellow-600">{metricas.pendientes}</span>
            </div>
            <div className="flex justify-between">
              <span>Errores:</span>
              <span className="font-bold text-red-600">{metricas.errores}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
