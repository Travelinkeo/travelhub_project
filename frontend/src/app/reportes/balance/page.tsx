'use client';

import { useState } from 'react';
import { api } from '@/lib/api';
import { Button, TextField } from '@mui/material';

interface CuentaBalance {
  cuenta: string;
  nombre: string;
  debe: number;
  haber: number;
  saldo: number;
  naturaleza: string;
}

export default function BalancePage() {
  const [fechaHasta, setFechaHasta] = useState('');
  const [balance, setBalance] = useState<CuentaBalance[]>([]);
  const [totales, setTotales] = useState<{ debe: number; haber: number; diferencia: number } | null>(null);
  const [loading, setLoading] = useState(false);

  const cargarBalance = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (fechaHasta) params.append('fecha_hasta', fechaHasta);
      
      const response = await api.get(`/api/reportes/balance-comprobacion/?${params}`);
      setBalance(response.data.balance || []);
      setTotales(response.data.totales);
    } catch (error) {
      console.error('Error:', error);
      alert('Error al cargar balance');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6">
      <h1 className="text-3xl font-bold mb-6">Balance de Comprobación</h1>

      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <div className="flex gap-4 items-end">
          <TextField
            label="Fecha de Corte"
            type="date"
            value={fechaHasta}
            onChange={(e) => setFechaHasta(e.target.value)}
            InputLabelProps={{ shrink: true }}
            size="small"
          />
          <Button variant="contained" onClick={cargarBalance} disabled={loading}>
            {loading ? 'Cargando...' : 'Consultar'}
          </Button>
        </div>
      </div>

      {balance.length > 0 && (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="min-w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Cuenta</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Nombre</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Debe</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Haber</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Saldo</th>
                <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase">Naturaleza</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {balance.map((cuenta) => (
                <tr key={cuenta.cuenta}>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">{cuenta.cuenta}</td>
                  <td className="px-6 py-4 text-sm">{cuenta.nombre}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-right">
                    ${cuenta.debe.toFixed(2)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-right">
                    ${cuenta.haber.toFixed(2)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-right font-bold">
                    ${cuenta.saldo.toFixed(2)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-center">
                    <span className={`px-2 py-1 rounded text-xs ${
                      cuenta.naturaleza === 'Deudora' ? 'bg-blue-100 text-blue-800' : 'bg-green-100 text-green-800'
                    }`}>
                      {cuenta.naturaleza}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
            {totales && (
              <tfoot className="bg-gray-50 font-bold">
                <tr>
                  <td colSpan={2} className="px-6 py-4 text-sm">TOTALES</td>
                  <td className="px-6 py-4 text-sm text-right">${totales.debe.toFixed(2)}</td>
                  <td className="px-6 py-4 text-sm text-right">${totales.haber.toFixed(2)}</td>
                  <td className="px-6 py-4 text-sm text-right" colSpan={2}>
                    <span className={totales.diferencia === 0 ? 'text-green-600' : 'text-red-600'}>
                      Diferencia: ${totales.diferencia.toFixed(2)}
                    </span>
                  </td>
                </tr>
              </tfoot>
            )}
          </table>
        </div>
      )}
    </div>
  );
}
