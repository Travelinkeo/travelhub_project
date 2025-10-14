'use client';

import { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import { Button, Chip, Dialog, DialogTitle, DialogContent, DialogActions, TextField } from '@mui/material';

interface Pasaporte {
  id: number;
  numero_pasaporte: string;
  nombre_completo: string;
  nacionalidad: string;
  fecha_nacimiento: string;
  fecha_vencimiento: string;
  confianza_ocr: number;
  verificado_manualmente: boolean;
  es_valido: boolean;
  cliente: number | null;
  imagen_original: string;
}

export default function PasaportesPage() {
  const [pasaportes, setPasaportes] = useState<Pasaporte[]>([]);
  const [filtro, setFiltro] = useState<'todos' | 'pendientes' | 'baja_confianza'>('todos');
  const [selectedPasaporte, setSelectedPasaporte] = useState<Pasaporte | null>(null);
  const [imageDialog, setImageDialog] = useState(false);

  const cargarPasaportes = async () => {
    try {
      let url = '/api/pasaportes/';
      if (filtro === 'pendientes') url = '/api/pasaportes/pendientes/';
      if (filtro === 'baja_confianza') url = '/api/pasaportes/baja_confianza/?umbral=0.7';
      
      const response = await api.get(url);
      setPasaportes(response.data.results || response.data);
    } catch (error) {
      console.error('Error cargando pasaportes:', error);
    }
  };

  useEffect(() => {
    cargarPasaportes();
  }, [filtro]);

  const verificarPasaporte = async (id: number) => {
    try {
      await api.post(`/api/pasaportes/${id}/verificar/`);
      alert('Pasaporte verificado');
      cargarPasaportes();
    } catch (error) {
      console.error('Error:', error);
      alert('Error al verificar');
    }
  };

  const crearCliente = async (id: number) => {
    try {
      const response = await api.post(`/api/pasaportes/${id}/crear_cliente/`);
      alert(`Cliente creado con ID: ${response.data.cliente_id}`);
      cargarPasaportes();
    } catch (error) {
      console.error('Error:', error);
      alert('Error al crear cliente');
    }
  };

  const uploadPasaporte = async (file: File) => {
    try {
      const formData = new FormData();
      formData.append('imagen_original', file);
      await api.post('/api/pasaportes/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      alert('Pasaporte procesado');
      cargarPasaportes();
    } catch (error) {
      console.error('Error:', error);
      alert('Error al procesar pasaporte');
    }
  };

  return (
    <div className="p-6">
      <h1 className="text-3xl font-bold mb-6">Gestión de Pasaportes OCR</h1>

      <div className="flex gap-4 mb-6">
        <Button variant={filtro === 'todos' ? 'contained' : 'outlined'} onClick={() => setFiltro('todos')}>
          Todos
        </Button>
        <Button variant={filtro === 'pendientes' ? 'contained' : 'outlined'} onClick={() => setFiltro('pendientes')}>
          Sin Cliente
        </Button>
        <Button variant={filtro === 'baja_confianza' ? 'contained' : 'outlined'} onClick={() => setFiltro('baja_confianza')}>
          Baja Confianza
        </Button>
        <input
          type="file"
          accept="image/*"
          onChange={(e) => e.target.files?.[0] && uploadPasaporte(e.target.files[0])}
          style={{ display: 'none' }}
          id="upload-pasaporte"
        />
        <label htmlFor="upload-pasaporte">
          <Button variant="contained" color="primary" component="span">
            Subir Pasaporte
          </Button>
        </label>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {pasaportes.map((pasaporte) => (
          <div key={pasaporte.id} className="bg-white rounded-lg shadow p-4">
            <div className="flex justify-between items-start mb-3">
              <div>
                <h3 className="font-bold text-lg">{pasaporte.nombre_completo}</h3>
                <p className="text-sm text-gray-600">{pasaporte.numero_pasaporte}</p>
              </div>
              <Chip 
                label={`${(pasaporte.confianza_ocr * 100).toFixed(0)}%`}
                color={pasaporte.confianza_ocr >= 0.7 ? 'success' : 'warning'}
                size="small"
              />
            </div>
            
            <div className="space-y-1 text-sm mb-3">
              <p><strong>Nacionalidad:</strong> {pasaporte.nacionalidad}</p>
              <p><strong>Nacimiento:</strong> {pasaporte.fecha_nacimiento}</p>
              <p><strong>Vencimiento:</strong> {pasaporte.fecha_vencimiento}</p>
              <p>
                <strong>Estado:</strong>{' '}
                {pasaporte.verificado_manualmente ? (
                  <Chip label="Verificado" color="success" size="small" />
                ) : (
                  <Chip label="Sin verificar" color="warning" size="small" />
                )}
              </p>
              <p>
                <strong>Cliente:</strong>{' '}
                {pasaporte.cliente ? `ID ${pasaporte.cliente}` : 'Sin asignar'}
              </p>
            </div>

            <div className="flex gap-2">
              <Button 
                size="small" 
                variant="outlined"
                onClick={() => {
                  setSelectedPasaporte(pasaporte);
                  setImageDialog(true);
                }}
              >
                Ver Imagen
              </Button>
              {!pasaporte.verificado_manualmente && (
                <Button 
                  size="small" 
                  variant="contained" 
                  color="primary"
                  onClick={() => verificarPasaporte(pasaporte.id)}
                >
                  Verificar
                </Button>
              )}
              {!pasaporte.cliente && (
                <Button 
                  size="small" 
                  variant="contained" 
                  color="success"
                  onClick={() => crearCliente(pasaporte.id)}
                >
                  Crear Cliente
                </Button>
              )}
            </div>
          </div>
        ))}
      </div>

      <Dialog open={imageDialog} onClose={() => setImageDialog(false)} maxWidth="md" fullWidth>
        <DialogTitle>Imagen del Pasaporte</DialogTitle>
        <DialogContent>
          {selectedPasaporte && (
            <img 
              src={`http://localhost:8000${selectedPasaporte.imagen_original}`} 
              alt="Pasaporte" 
              className="w-full"
            />
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setImageDialog(false)}>Cerrar</Button>
        </DialogActions>
      </Dialog>
    </div>
  );
}
