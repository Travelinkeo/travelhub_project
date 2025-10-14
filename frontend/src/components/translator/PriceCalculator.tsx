'use client';

import { useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';

interface CalculationResult {
  tarifa: number;
  fee_consolidador: number;
  fee_interno: number;
  suma_base: number;
  porcentaje: number;
  monto_porcentaje: number;
  precio_final: number;
  desglose: string;
}

export default function PriceCalculator() {
  const { token } = useAuth();
  const [tarifa, setTarifa] = useState('');
  const [feeConsolidador, setFeeConsolidador] = useState('');
  const [feeInterno, setFeeInterno] = useState('');
  const [porcentaje, setPorcentaje] = useState('');
  const [result, setResult] = useState<CalculationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const calculatePrice = async () => {
    const tarifaNum = parseFloat(tarifa) || 0;
    const feeConsolidadorNum = parseFloat(feeConsolidador) || 0;
    const feeInternoNum = parseFloat(feeInterno) || 0;
    const porcentajeNum = parseFloat(porcentaje) || 0;

    if (tarifaNum < 0 || feeConsolidadorNum < 0 || feeInternoNum < 0 || porcentajeNum < 0) {
      setError('Los valores no pueden ser negativos');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await fetch('/api/translator/calculate/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          tarifa: tarifaNum,
          fee_consolidador: feeConsolidadorNum,
          fee_interno: feeInternoNum,
          porcentaje: porcentajeNum,
        }),
      });

      const data = await response.json();
      if (data.success) {
        setResult(data.calculation);
      } else {
        setError(data.error || 'Error calculando precio');
      }
    } catch (error) {
      setError('Error de conexión');
    } finally {
      setLoading(false);
    }
  };

  const clearForm = () => {
    setTarifa('');
    setFeeConsolidador('');
    setFeeInterno('');
    setPorcentaje('');
    setResult(null);
    setError('');
  };

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Tarifa Base ($)
          </label>
          <input
            type="number"
            step="0.01"
            value={tarifa}
            onChange={(e) => setTarifa(e.target.value)}
            placeholder="100.00"
            className="w-full p-3 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Fee Consolidador ($)
          </label>
          <input
            type="number"
            step="0.01"
            value={feeConsolidador}
            onChange={(e) => setFeeConsolidador(e.target.value)}
            placeholder="25.00"
            className="w-full p-3 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Fee Interno ($)
          </label>
          <input
            type="number"
            step="0.01"
            value={feeInterno}
            onChange={(e) => setFeeInterno(e.target.value)}
            placeholder="15.00"
            className="w-full p-3 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Porcentaje de Ganancia (%)
          </label>
          <input
            type="number"
            step="0.1"
            value={porcentaje}
            onChange={(e) => setPorcentaje(e.target.value)}
            placeholder="10.0"
            className="w-full p-3 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>
      </div>

      <div className="flex space-x-4">
        <button
          onClick={calculatePrice}
          disabled={loading}
          className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? 'Calculando...' : 'Calcular Precio'}
        </button>
        <button
          onClick={clearForm}
          className="px-6 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700"
        >
          Limpiar
        </button>
      </div>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-md">
          <p className="text-red-600">{error}</p>
        </div>
      )}

      {result && (
        <div className="p-6 bg-green-50 border border-green-200 rounded-md">
          <h4 className="text-lg font-semibold mb-4">Cálculo de Precio</h4>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div className="space-y-2">
              <p><strong>Tarifa base:</strong> ${result.tarifa.toFixed(2)}</p>
              <p><strong>Fee consolidador:</strong> ${result.fee_consolidador.toFixed(2)}</p>
              <p><strong>Fee interno:</strong> ${result.fee_interno.toFixed(2)}</p>
              <p><strong>Subtotal:</strong> ${result.suma_base.toFixed(2)}</p>
            </div>
            <div className="space-y-2">
              <p><strong>Porcentaje:</strong> {result.porcentaje}%</p>
              <p><strong>Monto porcentaje:</strong> ${result.monto_porcentaje.toFixed(2)}</p>
              <p className="text-xl font-bold text-green-600">
                <strong>PRECIO FINAL: ${result.precio_final.toFixed(2)}</strong>
              </p>
            </div>
          </div>

          <div className="p-3 bg-white rounded border">
            <p className="text-sm text-gray-600">
              <strong>Desglose:</strong> {result.desglose}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}