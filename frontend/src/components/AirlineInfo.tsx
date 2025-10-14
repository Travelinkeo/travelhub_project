'use client';

import { useApiDetail } from '@/hooks/api';
import { Aerolinea } from '@/types/api';

interface AirlineInfoProps {
  airlineId?: number | string;
  airlineCode?: string;
  airlineName?: string;
  showCode?: boolean;
  className?: string;
}

export default function AirlineInfo({
  airlineId,
  airlineCode,
  airlineName,
  showCode = true,
  className = ""
}: AirlineInfoProps) {
  const { data: airline, isLoading } = useApiDetail<Aerolinea>(
    'aerolineas',
    airlineId || null
  );

  // Si tenemos datos directos, los usamos
  if (airlineCode && airlineName) {
    return (
      <span className={`inline-flex items-center ${className}`}>
        {showCode && (
          <span className="bg-blue-100 text-blue-800 text-xs font-medium px-2 py-1 rounded mr-2">
            {airlineCode}
          </span>
        )}
        <span className="text-gray-900">{airlineName}</span>
      </span>
    );
  }

  // Si estamos cargando desde la API
  if (isLoading) {
    return (
      <span className={`inline-flex items-center ${className}`}>
        <div className="animate-pulse bg-gray-200 h-4 w-20 rounded"></div>
      </span>
    );
  }

  // Si tenemos datos de la API
  if (airline) {
    return (
      <span className={`inline-flex items-center ${className}`}>
        {showCode && (
          <span className="bg-blue-100 text-blue-800 text-xs font-medium px-2 py-1 rounded mr-2">
            {airline.codigo_iata}
          </span>
        )}
        <span className="text-gray-900">{airline.nombre}</span>
        {!airline.activa && (
          <span className="ml-2 bg-red-100 text-red-800 text-xs font-medium px-2 py-1 rounded">
            Inactiva
          </span>
        )}
      </span>
    );
  }

  // Fallback si no hay datos
  return (
    <span className={`text-gray-500 ${className}`}>
      Aerolínea no especificada
    </span>
  );
}