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
  Checkbox,
  FormControlLabel,
  SelectChangeEvent
} from '@mui/material';
import Grid from '@mui/material/Grid'; // Importación directa

// Importar el tipo centralizado
import { Proveedor } from '@/types/api';

interface ProveedorFormProps {
  open: boolean;
  onClose: () => void;
  onSave: (proveedor: Partial<Proveedor>) => void;
  proveedor: Proveedor | null;
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
  maxHeight: '90vh',
  overflowY: 'auto',
};

const ProveedorForm: React.FC<ProveedorFormProps> = ({ open, onClose, onSave, proveedor }) => {
  const getInitialFormData = (): Partial<Proveedor> => ({
    nombre: '',
    tipo_proveedor: 'OTR',
    nivel_proveedor: 'DIR',
    activo: true,
    ...(proveedor || {}),
  });

  const [formData, setFormData] = useState<Partial<Proveedor>>(getInitialFormData());

  useEffect(() => {
    if (open) {
      setFormData(getInitialFormData());
    }
  }, [proveedor, open]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement> | SelectChangeEvent<string>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleCheckboxChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, checked } = e.target;
    setFormData(prev => ({ ...prev, [name]: checked }));
  };

  const handleSave = () => {
    onSave(formData);
  };

  return (
    <Modal open={open} onClose={onClose}>
      <Box sx={style}>
        <Typography variant="h6" component="h2">
          {proveedor ? 'Editar Proveedor' : 'Crear Nuevo Proveedor'}
        </Typography>
        <Grid container spacing={2} sx={{ mt: 2 }}>
          <Grid xs={12}>
            <TextField name="nombre" label="Nombre del Proveedor" value={formData.nombre || ''} onChange={handleChange} fullWidth required />
          </Grid>
          <Grid xs={6}>
            <FormControl fullWidth>
              <InputLabel>Tipo de Proveedor</InputLabel>
              <Select name="tipo_proveedor" value={formData.tipo_proveedor || 'OTR'} label="Tipo de Proveedor" onChange={handleChange}>
                <MenuItem value="AER">Aerolínea</MenuItem>
                <MenuItem value="HTL">Hotel</MenuItem>
                <MenuItem value="OPT">Operador Turístico</MenuItem>
                <MenuItem value="CON">Consolidador</MenuItem>
                <MenuItem value="MAY">Mayorista</MenuItem>
                <MenuItem value="SEG">Seguros</MenuItem>
                <MenuItem value="TRN">Transporte Terrestre</MenuItem>
                <MenuItem value="GDS">GDS</MenuItem>
                <MenuItem value="OTR">Otro</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          <Grid xs={6}>
            <FormControl fullWidth>
              <InputLabel>Nivel del Proveedor</InputLabel>
              <Select name="nivel_proveedor" value={formData.nivel_proveedor || 'DIR'} label="Nivel del Proveedor" onChange={handleChange}>
                <MenuItem value="DIR">Directo</MenuItem>
                <MenuItem value="CON">Consolidador</MenuItem>
                <MenuItem value="MAY">Mayorista</MenuItem>
                <MenuItem value="TER">Otro (Tercero)</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          <Grid xs={12}>
            <TextField name="contacto_nombre" label="Nombre de Contacto" value={formData.contacto_nombre || ''} onChange={handleChange} fullWidth />
          </Grid>
          <Grid xs={6}>
            <TextField name="contacto_email" label="Email de Contacto" type="email" value={formData.contacto_email || ''} onChange={handleChange} fullWidth />
          </Grid>
          <Grid xs={6}>
            <TextField name="contacto_telefono" label="Teléfono de Contacto" value={formData.contacto_telefono || ''} onChange={handleChange} fullWidth />
          </Grid>
          <Grid xs={12}>
            <TextField name="direccion" label="Dirección" value={formData.direccion || ''} onChange={handleChange} fullWidth />
          </Grid>
          <Grid xs={12}>
            <TextField name="notas" label="Notas" value={formData.notas || ''} onChange={handleChange} fullWidth multiline rows={3} />
          </Grid>
          <Grid xs={12}>
            <FormControlLabel
              control={<Checkbox checked={formData.activo} onChange={handleCheckboxChange} name="activo" />}
              label="Activo"
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

export default ProveedorForm;