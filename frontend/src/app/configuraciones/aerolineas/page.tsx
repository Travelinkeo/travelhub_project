'use client';

import { useState } from 'react';
import { useApiList, useApiCreate, useApiUpdate, useApiDelete } from '@/hooks/api';
import { Aerolinea } from '@/types/api';

export default function AerolineasPage() {
  const [searchTerm, setSearchTerm] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [editingAirline, setEditingAirline] = useState<Aerolinea | null>(null);
  
  const { data: airlines, isLoading, mutate } = useApiList<Aerolinea>('aerolineas');
  const { create, isCreating } = useApiCreate<Aerolinea>('aerolineas');
  const { update, isUpdating } = useApiUpdate<Aerolinea>('aerolineas', editingAirline?.id_aerolinea || 0);
  const { deleteItem, isDeleting } = useApiDelete('aerolineas', 0);

  const filteredAirlines = airlines?.filter(airline =>
    airline.nombre.toLowerCase().includes(searchTerm.toLowerCase()) ||
    airline.codigo_iata.toLowerCase().includes(searchTerm.toLowerCase())
  ) || [];

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    
    const airlineData: Partial<Aerolinea> = {
      codigo_iata: formData.get('codigo_iata') as string,
      nombre: formData.get('nombre') as string,
      activa: formData.get('activa') === 'on',
    };

    try {
      if (editingAirline) {
        await update(airlineData);
      } else {
        await create(airlineData as Aerolinea);
      }
      
      setShowForm(false);
      setEditingAirline(null);
      mutate();
    } catch (error) {
      console.error('Error saving airline:', error);
    }
  };

  const handleEdit = (airline: Aerolinea) => {
    setEditingAirline(airline);
    setShowForm(true);
  };

  const handleDelete = async (_id: number) => {
    if (confirm('¿Estás seguro de que quieres eliminar esta aerolínea?')) {
      try {
        await deleteItem();
        mutate();
      } catch (error) {
        console.error('Error deleting airline:', error);
      }
    }
  };

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Aerolíneas</h1>
        <button
          onClick={() => setShowForm(true)}
          className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded"
        >
          Nueva Aerolínea
        </button>
      </div>

      <div className="mb-6">
        <input
          type="text"
          placeholder="Buscar por nombre o código IATA..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
      </div>

      {showForm && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
            <h3 className="text-lg font-bold text-gray-900 mb-4">
              {editingAirline ? 'Editar Aerolínea' : 'Nueva Aerolínea'}
            </h3>
            
            <form onSubmit={handleSubmit}>
              <div className="mb-4">
                <label className="block text-gray-700 text-sm font-bold mb-2">
                  Código IATA
                </label>
                <input
                  type="text"
                  name="codigo_iata"
                  defaultValue={editingAirline?.codigo_iata || ''}
                  maxLength={2}
                  required
                  className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:border-blue-500"
                />
              </div>
              
              <div className="mb-4">
                <label className="block text-gray-700 text-sm font-bold mb-2">
                  Nombre
                </label>
                <input
                  type="text"
                  name="nombre"
                  defaultValue={editingAirline?.nombre || ''}
                  required
                  className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:border-blue-500"
                />
              </div>
              
              <div className="mb-4">
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    name="activa"
                    defaultChecked={editingAirline?.activa ?? true}
                    className="mr-2"
                  />
                  <span className="text-gray-700 text-sm font-bold">Activa</span>
                </label>
              </div>
              
              <div className="flex justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => {
                    setShowForm(false);
                    setEditingAirline(null);
                  }}
                  className="px-4 py-2 bg-gray-300 text-gray-700 rounded hover:bg-gray-400"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={isCreating || isUpdating}
                  className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50"
                >
                  {isCreating || isUpdating ? 'Guardando...' : 'Guardar'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <div className="bg-white shadow-md rounded-lg overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Código IATA
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Nombre
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Estado
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Acciones
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {filteredAirlines.map((airline) => (
              <tr key={airline.id_aerolinea} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                  {airline.codigo_iata}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {airline.nombre}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                    airline.activa 
                      ? 'bg-green-100 text-green-800' 
                      : 'bg-red-100 text-red-800'
                  }`}>
                    {airline.activa ? 'Activa' : 'Inactiva'}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                  <button
                    onClick={() => handleEdit(airline)}
                    className="text-indigo-600 hover:text-indigo-900 mr-4"
                  >
                    Editar
                  </button>
                  <button
                    onClick={() => handleDelete(airline.id_aerolinea!)}
                    disabled={isDeleting}
                    className="text-red-600 hover:text-red-900"
                  >
                    Eliminar
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        
        {filteredAirlines.length === 0 && (
          <div className="text-center py-8 text-gray-500">
            No se encontraron aerolíneas
          </div>
        )}
      </div>
      
      <div className="mt-4 text-sm text-gray-600">
        Total: {filteredAirlines.length} aerolíneas
      </div>
    </div>
  );
}