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
  SelectChangeEvent
} from '@mui/material';
import Grid from '@mui/material/Grid'; // Importación directa para Grid

// Paso 1: Importar el tipo desde el archivo centralizado usando el alias de ruta.
import { Cliente } from '@/types/api';

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
  width: 600,
  bgcolor: 'background.paper',
  border: '2px solid #000',
  boxShadow: 24,
  p: 4,
};

const ClienteForm: React.FC<ClienteFormProps> = ({ open, onClose, onSave, cliente }) => {
  // Usamos Partial<Cliente> para el estado del formulario, es más seguro.
  const [formData, setFormData] = useState<Partial<Cliente>>(cliente || { tipo_cliente: 'PAR' });

  useEffect(() => {
    // Actualizar el estado del formulario si el cliente a editar cambia
    setFormData(cliente || { tipo_cliente: 'PAR' });
  }, [cliente, open]);

  // Paso 2: Corregir el tipo del manejador de eventos para que sea compatible con Select y TextField
  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement> | SelectChangeEvent<string>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSave = () => {
    onSave(formData);
  };

  return (
    <Modal open={open} onClose={onClose}>
      <Box sx={style}>
        <Typography variant="h6" component="h2">
          {cliente ? 'Editar Cliente' : 'Crear Nuevo Cliente'}
        </Typography>
        {/* Paso 3: Corregir los componentes Grid eliminando la prop 'item' */}
        <Grid container spacing={2} sx={{ mt: 2 }}>
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

          {formData.tipo_cliente === 'PAR' ? (
            <>
              <Grid xs={6}>
                <TextField name="nombres" label="Nombres" value={formData.nombres || ''} onChange={handleChange} fullWidth />
              </Grid>
              <Grid xs={6}>
                <TextField name="apellidos" label="Apellidos" value={formData.apellidos || ''} onChange={handleChange} fullWidth />
              </Grid>
            </>
          ) : (
            <Grid xs={12}>
              <TextField name="nombre_empresa" label="Nombre de la Empresa" value={formData.nombre_empresa || ''} onChange={handleChange} fullWidth />
            </Grid>
          )}

          <Grid xs={12}>
            <TextField name="cedula_identidad" label="Cédula/RIF" value={formData.cedula_identidad || ''} onChange={handleChange} fullWidth />
          </Grid>
          <Grid xs={6}>
            <TextField name="email" label="Email" type="email" value={formData.email || ''} onChange={handleChange} fullWidth />
          </Grid>
          <Grid xs={6}>
            <TextField name="telefono_principal" label="Teléfono" value={formData.telefono_principal || ''} onChange={handleChange} fullWidth />
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