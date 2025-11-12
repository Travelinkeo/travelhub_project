'use client';

import { useState } from 'react';
import { solicitarAnulacion } from '@/lib/api/boletos';

export default function AnulacionesBoletos() {
  const [form, setForm] = useState({
    boleto: '',
    tipo_anulacion: 'VOL',
    motivo: '',
    monto_original: '',
    penalidad_aerolinea: '',
    fee_agencia: ''
  });
  const [loading, setLoading] = useState(false);
  const [resultado, setResultado] = useState<any>(null);

  const solicitar = async () => {
    setLoading(true);
    try {
      const data = await solicitarAnulacion({
        ...form,
        boleto: parseInt(form.boleto),
        monto_original: parseFloat(form.monto_original),
        penalidad_aerolinea: parseFloat(form.penalidad_aerolinea),
        fee_agencia: parseFloat(form.fee_agencia)
      });
      setResultado(data);
    } catch (error) {
      console.error('Error:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold mb-8">Solicitar Anulación</h1>
      
      <div className="bg-white p-6 rounded-lg shadow max-w-2xl">
        <div className="space-y-4">
          <div>
            <label className="block text-sm mb-2">ID Boleto</label>
            <input
              type="number"
              className="border p-2 rounded w-full"
              value={form.boleto}
              onChange={e => setForm({...form, boleto: e.target.value})}
            />
          </div>

          <div>
            <label className="block text-sm mb-2">Tipo de Anulación</label>
            <select
              className="border p-2 rounded w-full"
              value={form.tipo_anulacion}
              onChange={e => setForm({...form, tipo_anulacion: e.target.value})}
            >
              <option value="VOL">Voluntaria</option>
              <option value="INV">Involuntaria</option>
              <option value="CAM">Cambio de Itinerario</option>
            </select>
          </div>

          <div>
            <label className="block text-sm mb-2">Motivo</label>
            <textarea
              className="border p-2 rounded w-full"
              rows={3}
              value={form.motivo}
              onChange={e => setForm({...form, motivo: e.target.value})}
            />
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-sm mb-2">Monto Original</label>
              <input
                type="number"
                step="0.01"
                className="border p-2 rounded w-full"
                value={form.monto_original}
                onChange={e => setForm({...form, monto_original: e.target.value})}
              />
            </div>

            <div>
              <label className="block text-sm mb-2">Penalidad Aerolínea</label>
              <input
                type="number"
                step="0.01"
                className="border p-2 rounded w-full"
                value={form.penalidad_aerolinea}
                onChange={e => setForm({...form, penalidad_aerolinea: e.target.value})}
              />
            </div>

            <div>
              <label className="block text-sm mb-2">Fee Agencia</label>
              <input
                type="number"
                step="0.01"
                className="border p-2 rounded w-full"
                value={form.fee_agencia}
                onChange={e => setForm({...form, fee_agencia: e.target.value})}
              />
            </div>
          </div>

          <button
            onClick={solicitar}
            disabled={loading}
            className="w-full bg-red-600 text-white py-2 rounded hover:bg-red-700 disabled:bg-gray-400"
          >
            {loading ? 'Solicitando...' : 'Solicitar Anulación'}
          </button>
        </div>

        {resultado && (
          <div className="mt-6 p-4 bg-green-50 border border-green-200 rounded">
            <h3 className="font-bold mb-2">Anulación Solicitada</h3>
            <p>Monto a Reembolsar: <span className="font-bold">${resultado.monto_reembolso}</span></p>
            <p className="text-sm text-gray-600 mt-2">ID: {resultado.id_anulacion}</p>
          </div>
        )}
      </div>
    </div>
  );
}
