'use client';

import { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import { TextField, Chip, Dialog, DialogTitle, DialogContent, DialogActions, Button } from '@mui/material';

interface Comunicacion {
  id: number;
  remitente: string;
  asunto: string;
  fecha_recepcion: string;
  categoria: string;
  contenido_extraido: string;
  cuerpo_completo: string;
}

export default function InboxPage() {
  const [comunicaciones, setComunicaciones] = useState<Comunicacion[]>([]);
  const [categorias, setCategorias] = useState<Array<{ categoria: string; count: number }>>([]);
  const [search, setSearch] = useState('');
  const [selectedComunicacion, setSelectedComunicacion] = useState<Comunicacion | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);

  const cargarComunicaciones = async () => {
    try {
      const params = new URLSearchParams();
      if (search) params.append('search', search);
      
      const response = await api.get(`/api/comunicaciones/?${params}`);
      setComunicaciones(response.data.results || response.data);
    } catch (error) {
      console.error('Error:', error);
    }
  };

  const cargarCategorias = async () => {
    try {
      const response = await api.get('/api/comunicaciones/por_categoria/');
      setCategorias(response.data);
    } catch (error) {
      console.error('Error:', error);
    }
  };

  useEffect(() => {
    cargarComunicaciones();
    cargarCategorias();
  }, [search]);

  const verDetalle = (comunicacion: Comunicacion) => {
    setSelectedComunicacion(comunicacion);
    setDialogOpen(true);
  };

  const getCategoriaColor = (categoria: string) => {
    const colores: Record<string, any> = {
      RESERVA: 'primary',
      FACTURA: 'success',
      CANCELACION: 'error',
      CONSULTA: 'info',
      OTRO: 'default'
    };
    return colores[categoria] || 'default';
  };

  return (
    <div className="p-6">
      <h1 className="text-3xl font-bold mb-6">Inbox de Comunicaciones con Proveedores</h1>

      {/* Resumen por categorías */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
        {categorias.map((cat) => (
          <div key={cat.categoria} className="bg-white rounded-lg shadow p-4 text-center">
            <p className="text-sm text-gray-600">{cat.categoria}</p>
            <p className="text-2xl font-bold">{cat.count}</p>
          </div>
        ))}
      </div>

      {/* Búsqueda */}
      <div className="mb-6">
        <TextField
          label="Buscar en asunto, remitente o contenido"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          fullWidth
          size="small"
        />
      </div>

      {/* Lista de comunicaciones */}
      <div className="space-y-3">
        {comunicaciones.map((com) => (
          <div 
            key={com.id} 
            className="bg-white rounded-lg shadow p-4 hover:shadow-lg transition-shadow cursor-pointer"
            onClick={() => verDetalle(com)}
          >
            <div className="flex justify-between items-start mb-2">
              <div className="flex-1">
                <h3 className="font-bold text-lg">{com.asunto}</h3>
                <p className="text-sm text-gray-600">De: {com.remitente}</p>
              </div>
              <div className="text-right">
                <Chip 
                  label={com.categoria} 
                  color={getCategoriaColor(com.categoria)}
                  size="small"
                  className="mb-2"
                />
                <p className="text-xs text-gray-500">
                  {new Date(com.fecha_recepcion).toLocaleString()}
                </p>
              </div>
            </div>
            <p className="text-sm text-gray-700 line-clamp-2">
              {com.contenido_extraido || 'Sin contenido extraído'}
            </p>
          </div>
        ))}
      </div>

      {/* Dialog de detalle */}
      <Dialog 
        open={dialogOpen} 
        onClose={() => setDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          {selectedComunicacion?.asunto}
        </DialogTitle>
        <DialogContent>
          <div className="space-y-3">
            <div>
              <p className="text-sm font-bold">Remitente:</p>
              <p className="text-sm">{selectedComunicacion?.remitente}</p>
            </div>
            <div>
              <p className="text-sm font-bold">Fecha:</p>
              <p className="text-sm">
                {selectedComunicacion && new Date(selectedComunicacion.fecha_recepcion).toLocaleString()}
              </p>
            </div>
            <div>
              <p className="text-sm font-bold">Categoría:</p>
              <Chip 
                label={selectedComunicacion?.categoria} 
                color={getCategoriaColor(selectedComunicacion?.categoria || '')}
                size="small"
              />
            </div>
            <div>
              <p className="text-sm font-bold">Contenido Extraído:</p>
              <p className="text-sm whitespace-pre-wrap">
                {selectedComunicacion?.contenido_extraido || 'Sin contenido extraído'}
              </p>
            </div>
            <div>
              <p className="text-sm font-bold">Cuerpo Completo:</p>
              <div className="text-sm whitespace-pre-wrap bg-gray-50 p-3 rounded max-h-96 overflow-y-auto">
                {selectedComunicacion?.cuerpo_completo}
              </div>
            </div>
          </div>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Cerrar</Button>
        </DialogActions>
      </Dialog>
    </div>
  );
}
