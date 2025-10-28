'use client';

import React, { useState, useEffect } from 'react';
import {
  Modal,
  Box,
  Typography,
  TextField,
  Button,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  SelectChangeEvent,
  Checkbox,
  FormControlLabel,
  Autocomplete
} from '@mui/material';
import Grid from '@mui/material/Grid';

// Importar tipos y hooks
import { Cliente } from '@/types/api';
import { useApi } from '@/hooks/useApi';

interface Pais {
  id_pais: number;
  nombre: string;
  codigo_iso_2: string;
}

interface Ciudad {
  id_ciudad: number;
  nombre: string;
  pais: number;
}

// La interfaz local de Cliente ha sido eliminada.

interface ClienteFormProps {
  open: boolean;
  onClose: () => void;
  onSave: (cliente: Partial<Cliente>) => void; // Aceptamos un cliente parcial para la creación
  cliente: Cliente | null;
}

const style = {
  position: 'absolute' as 'absolute',
  top: '50%',
  left: '50%',
  transform: 'translate(-50%, -50%)',
  width: 800,
  maxHeight: '90vh',
  overflow: 'auto',
  bgcolor: 'background.paper',
  border: '2px solid #000',
  boxShadow: 24,
  p: 4,
};

const ClienteForm: React.FC<ClienteFormProps> = ({ open, onClose, onSave, cliente }) => {
  const [formData, setFormData] = useState<Partial<Cliente>>(cliente || { tipo_cliente: 'PAR' });
  
  // Cargar datos de países y ciudades (sin paginación)
  const { data: paisesResponse } = useApi<any>('/api/paises/?page_size=300');
  const { data: ciudadesResponse } = useApi<any>('/api/ciudades/?page_size=1000');
  
  const paises = Array.isArray(paisesResponse) ? paisesResponse : paisesResponse?.results || [];
  const ciudades = Array.isArray(ciudadesResponse) ? ciudadesResponse : ciudadesResponse?.results || [];
  
  console.log('Paises cargados:', paises.length);
  console.log('Ciudades cargadas:', ciudades.length);

  useEffect(() => {
    setFormData(cliente || { tipo_cliente: 'PAR' });
  }, [cliente, open]);

  // Paso 2: Corregir el tipo del manejador de eventos para que sea compatible con Select y TextField
  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement> | SelectChangeEvent<string>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSave = () => {
    console.log('Datos a guardar:', formData);
    onSave(formData);
  };

  return (
    <Modal open={open} onClose={onClose}>
      <Box sx={style}>
        <Typography variant="h6" component="h2">
          {cliente ? 'Editar Cliente' : 'Crear Nuevo Cliente'}
        </Typography>
        <Grid container spacing={2} sx={{ mt: 2 }}>
          {/* Tipo de Cliente */}
          <Grid component="div" xs={12}>
            <FormControl fullWidth>
              <InputLabel>Tipo de Cliente</InputLabel>
              <Select
                name="tipo_cliente"
                value={formData.tipo_cliente || 'PAR'}
                label="Tipo de Cliente"
                onChange={handleChange}
              >
                <MenuItem value="PAR">Particular</MenuItem>
                <MenuItem value="EMP">Empresa</MenuItem>
              </Select>
            </FormControl>
          </Grid>

          {/* Datos básicos según tipo */}
          {formData.tipo_cliente === 'PAR' ? (
            <>
              <Grid xs={6}>
                <TextField name="nombres" label="Nombres" value={formData.nombres || ''} onChange={handleChange} fullWidth required />
              </Grid>
              <Grid xs={6}>
                <TextField name="apellidos" label="Apellidos" value={formData.apellidos || ''} onChange={handleChange} fullWidth required />
              </Grid>
            </>
          ) : (
            <Grid xs={12}>
              <TextField name="nombre_empresa" label="Nombre de la Empresa" value={formData.nombre_empresa || ''} onChange={handleChange} fullWidth required />
            </Grid>
          )}

          {/* Documentos */}
          <Grid xs={6}>
            <TextField name="cedula_identidad" label="Cédula/RIF" value={formData.cedula_identidad || ''} onChange={handleChange} fullWidth />
          </Grid>
          <Grid xs={6}>
            <TextField name="numero_pasaporte" label="Número de Pasaporte" value={formData.numero_pasaporte || ''} onChange={handleChange} fullWidth />
          </Grid>

          {/* Contacto */}
          <Grid xs={6}>
            <TextField name="email" label="Email" type="email" value={formData.email || ''} onChange={handleChange} fullWidth />
          </Grid>
          <Grid xs={6}>
            <TextField name="telefono_principal" label="Teléfono" value={formData.telefono_principal || ''} onChange={handleChange} fullWidth />
          </Grid>

          {/* Fechas y Sexo */}
          <Grid xs={6}>
            <TextField 
              name="fecha_nacimiento" 
              label="Fecha de Nacimiento" 
              type="date" 
              value={formData.fecha_nacimiento || ''} 
              onChange={handleChange} 
              fullWidth 
              InputLabelProps={{ shrink: true }}
            />
          </Grid>
          <Grid xs={6}>
            <TextField 
              name="fecha_expiracion_pasaporte" 
              label="Fecha Expiración Pasaporte" 
              type="date" 
              value={formData.fecha_expiracion_pasaporte || ''} 
              onChange={handleChange} 
              fullWidth 
              InputLabelProps={{ shrink: true }}
            />
          </Grid>
          <Grid xs={6}>
            <FormControl fullWidth>
              <InputLabel>Sexo</InputLabel>
              <Select
                name="sexo"
                value={formData.sexo || ''}
                label="Sexo"
                onChange={handleChange}
              >
                <MenuItem value="">Sin especificar</MenuItem>
                <MenuItem value="M">Masculino</MenuItem>
                <MenuItem value="F">Femenino</MenuItem>
              </Select>
            </FormControl>
          </Grid>

          {/* Nacionalidad y País de Emisión */}
          <Grid xs={6}>
            <Autocomplete
              options={paises}
              getOptionLabel={(option) => option.nombre}
              value={paises.find(p => p.id_pais === formData.nacionalidad) || null}
              onChange={(_, newValue) => {
                setFormData(prev => ({ ...prev, nacionalidad: newValue?.id_pais || null }));
              }}
              isOptionEqualToValue={(option, value) => option.id_pais === value?.id_pais}
              renderInput={(params) => <TextField {...params} label="Nacionalidad" fullWidth />}
            />
          </Grid>
          <Grid xs={6}>
            <Autocomplete
              options={paises}
              getOptionLabel={(option) => option.nombre}
              value={paises.find(p => p.id_pais === formData.pais_emision_pasaporte) || null}
              onChange={(_, newValue) => {
                setFormData(prev => ({ ...prev, pais_emision_pasaporte: newValue?.id_pais || null }));
              }}
              isOptionEqualToValue={(option, value) => option.id_pais === value?.id_pais}
              renderInput={(params) => <TextField {...params} label="País Emisión Pasaporte" fullWidth />}
            />
          </Grid>

          {/* Dirección y Ciudad */}
          <Grid xs={8}>
            <TextField name="direccion" label="Dirección" value={formData.direccion || ''} onChange={handleChange} fullWidth multiline rows={2} />
          </Grid>
          <Grid xs={4}>
            <Autocomplete
              options={ciudades}
              getOptionLabel={(option) => option.nombre}
              value={ciudades.find(c => c.id_ciudad === formData.ciudad) || null}
              onChange={(_, newValue) => {
                setFormData(prev => ({ ...prev, ciudad: newValue?.id_ciudad || null }));
              }}
              isOptionEqualToValue={(option, value) => option.id_ciudad === value?.id_ciudad}
              renderInput={(params) => <TextField {...params} label="Ciudad" fullWidth />}
            />
          </Grid>

          {/* Puntos de Fidelidad y Cliente Frecuente */}
          <Grid xs={6}>
            <TextField 
              name="puntos_fidelidad" 
              label="Puntos de Fidelidad" 
              type="number" 
              value={formData.puntos_fidelidad || 0} 
              onChange={handleChange} 
              fullWidth 
            />
          </Grid>
          <Grid xs={6}>
            <FormControlLabel
              control={
                <Checkbox
                  checked={formData.es_cliente_frecuente || false}
                  onChange={(e) => setFormData(prev => ({ ...prev, es_cliente_frecuente: e.target.checked }))}
                />
              }
              label="Es Cliente Frecuente"
            />
          </Grid>
        </Grid>
        <Box sx={{ mt: 3, display: 'flex', justifyContent: 'flex-end' }}>
          <Button onClick={onClose} sx={{ mr: 1 }}>Cancelar</Button>
          <Button onClick={handleSave} variant="contained">Guardar</Button>
        </Box>
      </Box>
    </Modal>
  );
};

export default ClienteForm;