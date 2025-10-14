'use client';

import { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import { Button, Alert } from '@mui/material';

interface Problema {
  numero_asiento: string;
  fecha: string;
  debe: number;
  haber: number;
  diferencia: number;
}

export default function ValidacionPage() {
  const [validacion, setValidacion] = useState<{
    cuadrado: boolean;
    asientos_con_problemas: number;
    problemas: Problema[];
  } | null>(null);
  const [loading, setLoading] = useState(false);

  const validarCuadre = async () => {
    setLoading(true);
    try {
      const response = await api.get('/api/reportes/validar-cuadre/');
      setValidacion(response.data);
    } catch (error) {
      console.error('Error:', error);
      alert('Error al validar');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    validarCuadre();
  }, []);

  return (
    <div className="p-6">
      <h1 className="text-3xl font-bold mb-6">Validación de Cuadre Contable</h1>

      <div className="mb-6">
        <Button variant="contained" onClick={validarCuadre} disabled={loading}>
          {loading ? 'Validando...' : 'Validar Cuadre'}
        </Button>
      </div>

      {validacion && (
        <>
          <Alert severity={validacion.cuadrado ? 'success' : 'error'} className="mb-6">
            {validacion.cuadrado 
              ? '✓ Todos los asientos están cuadrados correctamente' 
              : `✗ Se encontraron ${validacion.asientos_con_problemas} asiento(s) con problemas`
            }
          </Alert>

          {!validacion.cuadrado && validacion.problemas.length > 0 && (
            <div className="bg-white rounded-lg shadow overflow-hidden">
              <div className="bg-red-50 px-6 py-3 border-b">
                <h2 className="font-bold text-lg text-red-800">Asientos Descuadrados</h2>
              </div>
              <table className="min-w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Número Asiento
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Fecha
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                      Debe
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                      Haber
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                      Diferencia
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {validacion.problemas.map((problema) => (
                    <tr key={problema.numero_asiento}>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                        {problema.numero_asiento}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        {problema.fecha}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-right">
                        ${problema.debe.toFixed(2)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-right">
                        ${problema.haber.toFixed(2)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-right font-bold text-red-600">
                        ${problema.diferencia.toFixed(2)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  );
}
