import { useMemo } from 'react';
import { useApiList } from './api';
import { Aerolinea } from '@/types/api';

export function useAirlines() {
  const { data: airlines, isLoading, error, mutate } = useApiList<Aerolinea>('aerolineas');

  const activeAirlines = useMemo(() => 
    airlines?.filter(airline => airline.activa) || [], 
    [airlines]
  );

  const airlineOptions = useMemo(() => 
    activeAirlines.map(airline => ({
      value: airline.id_aerolinea?.toString() || '',
      label: `${airline.codigo_iata} - ${airline.nombre}`,
      airline
    })), 
    [activeAirlines]
  );

  const getAirlineByCode = useMemo(() => 
    (code: string) => airlines?.find(airline => 
      airline.codigo_iata.toLowerCase() === code.toLowerCase()
    ), 
    [airlines]
  );

  const getAirlineById = useMemo(() => 
    (id: number | string) => airlines?.find(airline => 
      airline.id_aerolinea?.toString() === id.toString()
    ), 
    [airlines]
  );

  return {
    airlines: airlines || [],
    activeAirlines,
    airlineOptions,
    isLoading,
    error,
    mutate,
    getAirlineByCode,
    getAirlineById
  };
}