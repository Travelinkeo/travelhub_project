'use client';

import { useState } from 'react';
import { buscarBoletos } from '@/lib/api/boletos';
import type { Boleto } from '@/types/boletos';

export default function BuscarBoletos() {
  const [filtros, setFiltros] = useState({
    nombre: '',
    fecha_inicio: '',
    fecha_fin: '',
    origen: '',
    destino: '',
    aerolinea: '',
    pnr: ''
  });
  const [resultados, setResultados] = useState<Boleto[]>([]);
  const [loading, setLoading] = useState(false);

  const buscar = async () => {
    setLoading(true);
    try {
      const data = await buscarBoletos(filtros);
      setResultados(data);
    } catch (error) {
      console.error('Error:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold mb-8">Buscar Boletos</h1>
      
      <div className="bg-white p-6 rounded-lg shadow mb-8">
        <div className="grid grid-cols-2 gap-4 mb-4">
          <input
            className="border p-2 rounded"
            placeholder="Nombre pasajero"
            value={filtros.nombre}
            onChange={e => setFiltros({...filtros, nombre: e.target.value})}
          />
          
          <input
            className="border p-2 rounded"
            placeholder="PNR"
            value={filtros.pnr}
            onChange={e => setFiltros({...filtros, pnr: e.target.value})}
          />
          
          <input
            type="date"
            className="border p-2 rounded"
            value={filtros.fecha_inicio}
            onChange={e => setFiltros({...filtros, fecha_inicio: e.target.value})}
          />
          
          <input
            type="date"
            className="border p-2 rounded"
            value={filtros.fecha_fin}
            onChange={e => setFiltros({...filtros, fecha_fin: e.target.value})}
          />
          
          <input
            className="border p-2 rounded"
            placeholder="Origen (CCS)"
            value={filtros.origen}
            onChange={e => setFiltros({...filtros, origen: e.target.value})}
          />
          
          <input
            className="border p-2 rounded"
            placeholder="Destino (MIA)"
            value={filtros.destino}
            onChange={e => setFiltros({...filtros, destino: e.target.value})}
          />
        </div>
        
        <button
          onClick={buscar}
          disabled={loading}
          className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700 disabled:bg-gray-400"
        >
          {loading ? 'Buscando...' : 'Buscar'}
        </button>
      </div>

      <div className="space-y-4">
        {resultados.map(boleto => (
          <div key={boleto.id_boleto_importado} className="bg-white p-6 rounded-lg shadow">
            <div className="flex justify-between items-start">
              <div>
                <h3 className="text-xl font-bold">{boleto.numero_boleto}</h3>
                <p className="text-gray-600">{boleto.nombre_pasajero_procesado}</p>
                <p className="text-sm text-gray-500">{boleto.aerolinea_emisora}</p>
              </div>
              <div className="text-right">
                <p className="text-2xl font-bold">${boleto.total_boleto}</p>
                <p className="text-sm text-gray-500">PNR: {boleto.localizador_pnr}</p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
