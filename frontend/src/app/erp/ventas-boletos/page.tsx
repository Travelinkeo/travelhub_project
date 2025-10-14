'use client';

import { useState, useEffect } from 'react';

interface Pasajero {
  id: number;
  apellidos: string;
  nombres: string;
  tipo: string;
  documento: string;
}

interface Venta {
  id: number;
  localizador: string;
  numero_boleto: string;
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
}

interface Stats {
  total_ventas: number;
  total_boletos: number;
  total_ingresos: number;
  total_margen: number;
}

export default function VentasBoletosPage() {
  const [ventas, setVentas] = useState<Venta[]>([]);
  const [stats, setStats] = useState<Stats>({ total_ventas: 0, total_boletos: 0, total_ingresos: 0, total_margen: 0 });
  const [loading, setLoading] = useState(true);
  const [filtros, setFiltros] = useState({ localizador: '', fecha_desde: '', fecha_hasta: '' });

  useEffect(() => {
    cargarVentas();
  }, []);

  const cargarVentas = async (filtrosCustom = filtros) => {
    try {
      const params = new URLSearchParams(filtrosCustom as any);
      const response = await fetch(`http://127.0.0.1:8000/api/ventas-boletos/?${params}`);
      const data = await response.json();
      setVentas(data.ventas);
      setStats(data.stats);
    } catch (error) {
      console.error('Error al cargar ventas:', error);
    } finally {
      setLoading(false);
    }
  };

  const aplicarFiltros = () => {
    cargarVentas(filtros);
  };

  const limpiarFiltros = () => {
    const nuevosFiltros = { localizador: '', fecha_desde: '', fecha_hasta: '' };
    setFiltros(nuevosFiltros);
    cargarVentas(nuevosFiltros);
  };

  return (
    <div className="p-6 max-w-[1400px] mx-auto">
      <h1 className="text-2xl font-bold mb-6">📊 Dashboard de Ventas de Boletos</h1>

      {/* Filtros */}
      <div className="bg-gray-50 p-4 rounded-lg mb-6 flex gap-4 flex-wrap">
        <input
          type="text"
          placeholder="🔍 Buscar por localizador..."
          value={filtros.localizador}
          onChange={(e) => setFiltros({ ...filtros, localizador: e.target.value })}
          className="px-3 py-2 border rounded"
        />
        <input
          type="date"
          value={filtros.fecha_desde}
          onChange={(e) => setFiltros({ ...filtros, fecha_desde: e.target.value })}
          className="px-3 py-2 border rounded"
        />
        <input
          type="date"
          value={filtros.fecha_hasta}
          onChange={(e) => setFiltros({ ...filtros, fecha_hasta: e.target.value })}
          className="px-3 py-2 border rounded"
        />
        <button onClick={aplicarFiltros} className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
          Buscar
        </button>
        <button onClick={limpiarFiltros} className="bg-gray-600 text-white px-4 py-2 rounded hover:bg-gray-700">
          Limpiar
        </button>
      </div>

      {/* Estadísticas */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-gradient-to-br from-purple-500 to-purple-700 text-white p-5 rounded-lg">
          <h3 className="text-sm opacity-90 mb-2">Total Ventas</h3>
          <p className="text-3xl font-bold">{stats.total_ventas}</p>
        </div>
        <div className="bg-gradient-to-br from-purple-500 to-purple-700 text-white p-5 rounded-lg">
          <h3 className="text-sm opacity-90 mb-2">Total Boletos</h3>
          <p className="text-3xl font-bold">{stats.total_boletos}</p>
        </div>
        <div className="bg-gradient-to-br from-purple-500 to-purple-700 text-white p-5 rounded-lg">
          <h3 className="text-sm opacity-90 mb-2">Ingresos</h3>
          <p className="text-3xl font-bold">${stats.total_ingresos.toFixed(2)}</p>
        </div>
        <div className="bg-gradient-to-br from-purple-500 to-purple-700 text-white p-5 rounded-lg">
          <h3 className="text-sm opacity-90 mb-2">Margen</h3>
          <p className="text-3xl font-bold">${stats.total_margen.toFixed(2)}</p>
        </div>
      </div>

      {/* Tabla */}
      <div className="bg-white rounded-lg shadow overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-800 text-white">
            <tr>
              <th className="px-3 py-3 text-left">Localizador</th>
              <th className="px-3 py-3 text-left">Nº Boleto</th>
              <th className="px-3 py-3 text-left">Fecha</th>
              <th className="px-3 py-3 text-left">Cliente</th>
              <th className="px-3 py-3 text-left">Pasajeros</th>
              <th className="px-3 py-3 text-left">Aerolínea</th>
              <th className="px-3 py-3 text-left">Proveedor</th>
              <th className="px-3 py-3 text-left">Total</th>
              <th className="px-3 py-3 text-left">Estado</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={9} className="text-center py-10 text-gray-500">Cargando datos...</td>
              </tr>
            ) : ventas.length === 0 ? (
              <tr>
                <td colSpan={9} className="text-center py-10 text-gray-500">No se encontraron ventas</td>
              </tr>
            ) : (
              ventas.map((venta) => (
                <tr key={venta.id} className="border-b hover:bg-gray-50">
                  <td className="px-3 py-3 font-bold">{venta.localizador}</td>
                  <td className="px-3 py-3">{venta.numero_boleto}</td>
                  <td className="px-3 py-3">{new Date(venta.fecha).toLocaleDateString('es-ES')}</td>
                  <td className="px-3 py-3">{venta.cliente}</td>
                  <td className="px-3 py-3 text-xs text-gray-600">
                    {venta.pasajeros.map((p, i) => (
                      <div key={i}>{p.apellidos}</div>
                    ))}
                  </td>
                  <td className="px-3 py-3">{venta.aerolinea}</td>
                  <td className="px-3 py-3">{venta.proveedores.join(', ')}</td>
                  <td className="px-3 py-3">${venta.total_venta.toFixed(2)}</td>
                  <td className="px-3 py-3">
                    <span className="px-2 py-1 rounded text-xs font-semibold bg-yellow-100 text-yellow-800">
                      {venta.estado_display}
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
