'use client';

import { useAirlines } from '@/hooks/useAirlines';

export default function AirlineStats() {
  const { airlines, activeAirlines, isLoading } = useAirlines();

  if (isLoading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Aerolíneas</h3>
        <div className="animate-pulse space-y-3">
          <div className="h-4 bg-gray-200 rounded w-3/4"></div>
          <div className="h-4 bg-gray-200 rounded w-1/2"></div>
        </div>
      </div>
    );
  }

  const inactiveCount = airlines.length - activeAirlines.length;

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-medium text-gray-900 mb-4">Aerolíneas</h3>
      
      <div className="space-y-4">
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-600">Total</span>
          <span className="text-2xl font-bold text-gray-900">{airlines.length}</span>
        </div>
        
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-600">Activas</span>
          <span className="text-lg font-semibold text-green-600">{activeAirlines.length}</span>
        </div>
        
        {inactiveCount > 0 && (
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-600">Inactivas</span>
            <span className="text-lg font-semibold text-red-600">{inactiveCount}</span>
          </div>
        )}
        
        <div className="pt-4 border-t border-gray-200">
          <div className="text-xs text-gray-500 mb-2">Aerolíneas más comunes:</div>
          <div className="space-y-1">
            {activeAirlines.slice(0, 5).map((airline) => (
              <div key={airline.id_aerolinea} className="flex items-center justify-between text-xs">
                <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded font-mono">
                  {airline.codigo_iata}
                </span>
                <span className="text-gray-600 truncate ml-2 flex-1">
                  {airline.nombre}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}