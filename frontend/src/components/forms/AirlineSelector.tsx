'use client';

import { useState, useEffect } from 'react';
import { useApiList } from '@/hooks/api';
import { Aerolinea } from '@/types/api';

interface AirlineSelectorProps {
  value?: string;
  onChange: (airlineId: string, airline?: Aerolinea) => void;
  placeholder?: string;
  required?: boolean;
  className?: string;
}

export default function AirlineSelector({
  value,
  onChange,
  placeholder = "Seleccionar aerolínea...",
  required = false,
  className = ""
}: AirlineSelectorProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const [selectedAirline, setSelectedAirline] = useState<Aerolinea | null>(null);

  const { data: airlines, isLoading } = useApiList<Aerolinea>('aerolineas');

  const filteredAirlines = airlines?.filter(airline =>
    airline.activa && (
      airline.nombre.toLowerCase().includes(searchTerm.toLowerCase()) ||
      airline.codigo_iata.toLowerCase().includes(searchTerm.toLowerCase())
    )
  ) || [];

  useEffect(() => {
    if (value && airlines) {
      const airline = airlines.find(a => a.id_aerolinea?.toString() === value);
      setSelectedAirline(airline || null);
    }
  }, [value, airlines]);

  const handleSelect = (airline: Aerolinea) => {
    setSelectedAirline(airline);
    onChange(airline.id_aerolinea?.toString() || '', airline);
    setIsOpen(false);
    setSearchTerm('');
  };

  const handleClear = () => {
    setSelectedAirline(null);
    onChange('');
    setSearchTerm('');
  };

  return (
    <div className={`relative ${className}`}>
      <div className="relative">
        <input
          type="text"
          value={selectedAirline ? `${selectedAirline.codigo_iata} - ${selectedAirline.nombre}` : searchTerm}
          onChange={(e) => {
            setSearchTerm(e.target.value);
            setIsOpen(true);
            if (!e.target.value) {
              handleClear();
            }
          }}
          onFocus={() => setIsOpen(true)}
          placeholder={placeholder}
          required={required}
          className="w-full px-3 py-2 pr-10 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
        
        {selectedAirline && (
          <button
            type="button"
            onClick={handleClear}
            className="absolute right-8 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
          >
            ✕
          </button>
        )}
        
        <button
          type="button"
          onClick={() => setIsOpen(!isOpen)}
          className="absolute right-2 top-1/2 transform -translate-y-1/2 text-gray-400"
        >
          ▼
        </button>
      </div>

      {isOpen && (
        <div className="absolute z-50 w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg max-h-60 overflow-auto">
          {isLoading ? (
            <div className="px-3 py-2 text-gray-500">Cargando...</div>
          ) : filteredAirlines.length > 0 ? (
            filteredAirlines.map((airline) => (
              <button
                key={airline.id_aerolinea}
                type="button"
                onClick={() => handleSelect(airline)}
                className="w-full px-3 py-2 text-left hover:bg-gray-100 focus:bg-gray-100 focus:outline-none"
              >
                <div className="flex items-center justify-between">
                  <span className="font-medium">{airline.codigo_iata}</span>
                  <span className="text-gray-600 text-sm">{airline.nombre}</span>
                </div>
              </button>
            ))
          ) : (
            <div className="px-3 py-2 text-gray-500">
              {searchTerm ? 'No se encontraron aerolíneas' : 'No hay aerolíneas disponibles'}
            </div>
          )}
        </div>
      )}
    </div>
  );
}