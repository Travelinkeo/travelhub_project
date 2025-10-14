'use client';

import { useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';

interface BatchItem {
  id: string;
  itinerary: string;
  gds_system: string;
}

interface BatchResult {
  id: string;
  success: boolean;
  translated_itinerary?: string;
  error?: string;
  gds_system?: string;
}

export default function BatchTranslator() {
  const { token } = useAuth();
  const [items, setItems] = useState<BatchItem[]>([
    { id: 'item_1', itinerary: '', gds_system: 'SABRE' }
  ]);
  const [results, setResults] = useState<BatchResult[]>([]);
  const [summary, setSummary] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const addItem = () => {
    if (items.length >= 10) {
      setError('Máximo 10 itinerarios por lote');
      return;
    }
    setItems([...items, { 
      id: `item_${items.length + 1}`, 
      itinerary: '', 
      gds_system: 'SABRE' 
    }]);
  };

  const removeItem = (index: number) => {
    if (items.length > 1) {
      setItems(items.filter((_, i) => i !== index));
    }
  };

  const updateItem = (index: number, field: keyof BatchItem, value: string) => {
    const newItems = [...items];
    newItems[index] = { ...newItems[index], [field]: value };
    setItems(newItems);
  };

  const translateBatch = async () => {
    const validItems = items.filter(item => item.itinerary.trim());
    
    if (validItems.length === 0) {
      setError('Debe ingresar al menos un itinerario');
      return;
    }

    setLoading(true);
    setError('');
    setResults([]);
    setSummary(null);

    try {
      const response = await fetch('/api/translator/batch/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          itineraries: validItems,
        }),
      });

      const data = await response.json();
      if (data.success) {
        setResults(data.results);
        setSummary(data.summary);
      } else {
        setError(data.error || 'Error procesando lote');
      }
    } catch (error) {
      setError('Error de conexión');
    } finally {
      setLoading(false);
    }
  };

  const clearAll = () => {
    setItems([{ id: 'item_1', itinerary: '', gds_system: 'SABRE' }]);
    setResults([]);
    setSummary(null);
    setError('');
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-semibold">Itinerarios ({items.length}/10)</h3>
        <div className="space-x-2">
          <button
            onClick={addItem}
            disabled={items.length >= 10}
            className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50"
          >
            Agregar
          </button>
          <button
            onClick={clearAll}
            className="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700"
          >
            Limpiar Todo
          </button>
        </div>
      </div>

      <div className="space-y-4">
        {items.map((item, index) => (
          <div key={item.id} className="p-4 border border-gray-200 rounded-md">
            <div className="flex justify-between items-center mb-3">
              <h4 className="font-medium">Itinerario {index + 1}</h4>
              {items.length > 1 && (
                <button
                  onClick={() => removeItem(index)}
                  className="text-red-600 hover:text-red-800"
                >
                  Eliminar
                </button>
              )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  ID
                </label>
                <input
                  type="text"
                  value={item.id}
                  onChange={(e) => updateItem(index, 'id', e.target.value)}
                  className="w-full p-2 border border-gray-300 rounded-md"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Sistema GDS
                </label>
                <select
                  value={item.gds_system}
                  onChange={(e) => updateItem(index, 'gds_system', e.target.value)}
                  className="w-full p-2 border border-gray-300 rounded-md"
                >
                  <option value="SABRE">SABRE</option>
                  <option value="AMADEUS">AMADEUS</option>
                  <option value="KIU">KIU</option>
                </select>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Itinerario
              </label>
              <textarea
                value={item.itinerary}
                onChange={(e) => updateItem(index, 'itinerary', e.target.value)}
                placeholder="Ingrese el itinerario aquí..."
                rows={3}
                className="w-full p-2 border border-gray-300 rounded-md"
              />
            </div>
          </div>
        ))}
      </div>

      <div className="flex justify-center">
        <button
          onClick={translateBatch}
          disabled={loading}
          className="px-8 py-3 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? 'Procesando...' : 'Traducir Lote'}
        </button>
      </div>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-md">
          <p className="text-red-600">{error}</p>
        </div>
      )}

      {summary && (
        <div className="p-4 bg-blue-50 border border-blue-200 rounded-md">
          <h4 className="font-semibold mb-2">Resumen del Procesamiento</h4>
          <div className="grid grid-cols-3 gap-4 text-center">
            <div>
              <p className="text-2xl font-bold text-blue-600">{summary.total}</p>
              <p className="text-sm text-gray-600">Total</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-green-600">{summary.successful}</p>
              <p className="text-sm text-gray-600">Exitosos</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-red-600">{summary.failed}</p>
              <p className="text-sm text-gray-600">Fallidos</p>
            </div>
          </div>
        </div>
      )}

      {results.length > 0 && (
        <div className="space-y-4">
          <h4 className="text-lg font-semibold">Resultados</h4>
          {results.map((result, index) => (
            <div
              key={result.id}
              className={`p-4 border rounded-md ${
                result.success
                  ? 'border-green-200 bg-green-50'
                  : 'border-red-200 bg-red-50'
              }`}
            >
              <div className="flex justify-between items-center mb-2">
                <h5 className="font-medium">{result.id}</h5>
                <span
                  className={`px-2 py-1 rounded text-sm ${
                    result.success
                      ? 'bg-green-100 text-green-800'
                      : 'bg-red-100 text-red-800'
                  }`}
                >
                  {result.success ? 'Éxito' : 'Error'}
                </span>
              </div>

              {result.success && result.translated_itinerary ? (
                <div
                  className="prose max-w-none"
                  dangerouslySetInnerHTML={{ __html: result.translated_itinerary }}
                />
              ) : (
                <p className="text-red-600">{result.error}</p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}