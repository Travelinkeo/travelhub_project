'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';

interface GDSSystem {
  code: string;
  name: string;
  description: string;
}

export default function ItineraryTranslator() {
  const { token } = useAuth();
  const [itinerary, setItinerary] = useState('');
  const [gdsSystem, setGdsSystem] = useState('SABRE');
  const [supportedGDS, setSupportedGDS] = useState<GDSSystem[]>([]);
  const [translatedResult, setTranslatedResult] = useState('');
  const [validationResult, setValidationResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    loadSupportedGDS();
  }, []);

  const loadSupportedGDS = async () => {
    try {
      const response = await fetch('/api/translator/gds/', {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      const data = await response.json();
      if (data.success) {
        setSupportedGDS(data.supported_gds);
      }
    } catch (error) {
      console.error('Error loading GDS systems:', error);
    }
  };

  const validateItinerary = async () => {
    if (!itinerary.trim()) {
      setError('Por favor ingrese un itinerario');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await fetch('/api/translator/validate/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          itinerary,
          gds_system: gdsSystem,
        }),
      });

      const data = await response.json();
      if (data.success) {
        setValidationResult(data.validation);
      } else {
        setError(data.error || 'Error validando itinerario');
      }
    } catch (error) {
      setError('Error de conexión');
    } finally {
      setLoading(false);
    }
  };

  const translateItinerary = async () => {
    if (!itinerary.trim()) {
      setError('Por favor ingrese un itinerario');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await fetch('/api/translator/itinerary/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          itinerary,
          gds_system: gdsSystem,
        }),
      });

      const data = await response.json();
      if (data.success) {
        setTranslatedResult(data.translated_itinerary);
        setValidationResult(null);
      } else {
        setError(data.error || 'Error traduciendo itinerario');
      }
    } catch (error) {
      setError('Error de conexión');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Sistema GDS
          </label>
          <select
            value={gdsSystem}
            onChange={(e) => setGdsSystem(e.target.value)}
            className="w-full p-3 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            {supportedGDS.map((gds) => (
              <option key={gds.code} value={gds.code}>
                {gds.name} - {gds.description}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Itinerario
        </label>
        <textarea
          value={itinerary}
          onChange={(e) => setItinerary(e.target.value)}
          placeholder="Ingrese el itinerario aquí..."
          rows={6}
          className="w-full p-3 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
      </div>

      <div className="flex space-x-4">
        <button
          onClick={validateItinerary}
          disabled={loading}
          className="px-6 py-2 bg-yellow-600 text-white rounded-md hover:bg-yellow-700 disabled:opacity-50"
        >
          {loading ? 'Validando...' : 'Validar Formato'}
        </button>
        <button
          onClick={translateItinerary}
          disabled={loading}
          className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? 'Traduciendo...' : 'Traducir'}
        </button>
      </div>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-md">
          <p className="text-red-600">{error}</p>
        </div>
      )}

      {validationResult && (
        <div className="p-4 bg-gray-50 border border-gray-200 rounded-md">
          <h4 className="font-semibold mb-2">Resultado de Validación</h4>
          <p className={`mb-2 ${validationResult.is_valid ? 'text-green-600' : 'text-red-600'}`}>
            Estado: {validationResult.is_valid ? '✅ Válido' : '❌ Inválido'}
          </p>
          <p>Líneas totales: {validationResult.total_lines}</p>
          <p>Líneas válidas: {validationResult.valid_lines}</p>
          
          {validationResult.invalid_lines.length > 0 && (
            <div className="mt-3">
              <h5 className="font-medium text-red-600">Líneas con errores:</h5>
              <ul className="list-disc list-inside text-sm text-red-600">
                {validationResult.invalid_lines.map((line: any, index: number) => (
                  <li key={index}>
                    Línea {line.line_number}: {line.reason}
                  </li>
                ))}
              </ul>
            </div>
          )}
          
          {validationResult.warnings.length > 0 && (
            <div className="mt-3">
              <h5 className="font-medium text-yellow-600">Advertencias:</h5>
              <ul className="list-disc list-inside text-sm text-yellow-600">
                {validationResult.warnings.map((warning: string, index: number) => (
                  <li key={index}>{warning}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {translatedResult && (
        <div className="p-4 bg-green-50 border border-green-200 rounded-md">
          <h4 className="font-semibold mb-3">Itinerario Traducido ({gdsSystem})</h4>
          <div 
            className="prose max-w-none"
            dangerouslySetInnerHTML={{ __html: translatedResult }}
          />
        </div>
      )}
    </div>
  );
}