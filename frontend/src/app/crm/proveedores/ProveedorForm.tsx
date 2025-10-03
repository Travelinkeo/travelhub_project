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
  Autocomplete,
  Accordion,
  AccordionSummary,
  AccordionDetails
} from '@mui/material';
import Grid from '@mui/material/Grid';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';

// Importar tipos y hooks
import { Proveedor } from '@/types/api';
import { useApi } from '@/hooks/useApi';

interface Ciudad {
  id: number;
  nombre: string;
  pais: number;
}

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
  width: 900,
  maxHeight: '90vh',
  overflow: 'auto',
  bgcolor: 'background.paper',
  border: '2px solid #000',
  boxShadow: 24,
  p: 4,
};

const ProveedorForm: React.FC<ProveedorFormProps> = ({ open, onClose, onSave, proveedor }) => {
  const [formData, setFormData] = useState<Partial<Proveedor>>(proveedor || { activo: true });
  
  // Cargar ciudades
  const { data: ciudades } = useApi<Ciudad[]>('/api/ciudades/');

  useEffect(() => {
    setFormData(proveedor || { activo: true });
  }, [proveedor, open]);

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
          {proveedor ? 'Editar Proveedor' : 'Crear Nuevo Proveedor'}
        </Typography>
        
        {/* Información Básica */}
        <Accordion defaultExpanded>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="subtitle1">Información Básica</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Grid container spacing={2}>
              <Grid xs={12}>
                <TextField
                  name="nombre"
                  label="Nombre del Proveedor"
                  value={formData.nombre || ''}
                  onChange={handleChange}
                  fullWidth
                  required
                />
              </Grid>
              <Grid xs={6}>
                <FormControl fullWidth>
                  <InputLabel>Tipo de Proveedor</InputLabel>
                  <Select
                    name="tipo_proveedor"
                    value={formData.tipo_proveedor || 'OTR'}
                    label="Tipo de Proveedor"
                    onChange={handleChange}
                  >
                    <MenuItem value="AER">Aerolínea</MenuItem>
                    <MenuItem value="HTL">Hotel</MenuItem>
                    <MenuItem value="OPT">Operador Turístico</MenuItem>
                    <MenuItem value="CON">Consolidador</MenuItem>
                    <MenuItem value="MAY">Mayorista</MenuItem>
                    <MenuItem value="SEG">Seguros</MenuItem>
                    <MenuItem value="TRN">Transporte Terrestre</MenuItem>
                    <MenuItem value="GDS">Sistema de Distribución Global (GDS)</MenuItem>
                    <MenuItem value="OTR">Otro</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              <Grid xs={6}>
                <FormControl fullWidth>
                  <InputLabel>Nivel del Proveedor</InputLabel>
                  <Select
                    name="nivel_proveedor"
                    value={formData.nivel_proveedor || 'DIR'}
                    label="Nivel del Proveedor"
                    onChange={handleChange}
                  >
                    <MenuItem value="DIR">Directo</MenuItem>
                    <MenuItem value="CON">Consolidador</MenuItem>
                    <MenuItem value="MAY">Mayorista</MenuItem>
                    <MenuItem value="TER">Otro (Tercero)</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              <Grid xs={12}>
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={formData.activo !== false}
                      onChange={(e) => setFormData(prev => ({ ...prev, activo: e.target.checked }))}
                    />
                  }
                  label="Activo"
                />
              </Grid>
            </Grid>
          </AccordionDetails>
        </Accordion>

        {/* Información de Contacto */}
        <Accordion>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="subtitle1">Información de Contacto</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Grid container spacing={2}>
              <Grid xs={12}>
                <TextField
                  name="contacto_nombre"
                  label="Nombre de Contacto"
                  value={formData.contacto_nombre || ''}
                  onChange={handleChange}
                  fullWidth
                />
              </Grid>
              <Grid xs={6}>
                <TextField
                  name="contacto_email"
                  label="Email de Contacto"
                  type="email"
                  value={formData.contacto_email || ''}
                  onChange={handleChange}
                  fullWidth
                />
              </Grid>
              <Grid xs={6}>
                <TextField
                  name="contacto_telefono"
                  label="Teléfono de Contacto"
                  value={formData.contacto_telefono || ''}
                  onChange={handleChange}
                  fullWidth
                />
              </Grid>
              <Grid xs={8}>
                <TextField
                  name="direccion"
                  label="Dirección"
                  value={formData.direccion || ''}
                  onChange={handleChange}
                  fullWidth
                  multiline
                  rows={2}
                />
              </Grid>
              <Grid xs={4}>
                <Autocomplete
                  options={Array.isArray(ciudades) ? ciudades : []}
                  getOptionLabel={(option) => option.nombre}
                  value={Array.isArray(ciudades) ? ciudades.find(c => c.id === formData.ciudad) || null : null}
                  onChange={(_, newValue) => {
                    setFormData(prev => ({ ...prev, ciudad: newValue?.id || null }));
                  }}
                  renderInput={(params) => <TextField {...params} label="Ciudad" fullWidth />}
                />
              </Grid>
            </Grid>
          </AccordionDetails>
        </Accordion>

        {/* Información Comercial */}
        <Accordion>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="subtitle1">Información Comercial</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Grid container spacing={2}>
              <Grid xs={6}>
                <TextField
                  name="numero_cuenta_agencia"
                  label="Número de Cuenta/IATA"
                  value={formData.numero_cuenta_agencia || ''}
                  onChange={handleChange}
                  fullWidth
                />
              </Grid>
              <Grid xs={6}>
                <TextField
                  name="condiciones_pago"
                  label="Condiciones de Pago"
                  value={formData.condiciones_pago || ''}
                  onChange={handleChange}
                  fullWidth
                />
              </Grid>
              <Grid xs={12}>
                <TextField
                  name="datos_bancarios"
                  label="Datos Bancarios del Proveedor"
                  value={formData.datos_bancarios || ''}
                  onChange={handleChange}
                  fullWidth
                  multiline
                  rows={3}
                />
              </Grid>
            </Grid>
          </AccordionDetails>
        </Accordion>

        {/* Identificación GDS y Sistemas */}
        <Accordion>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="subtitle1">Identificación GDS y Sistemas</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Grid container spacing={2}>
              <Grid xs={6}>
                <TextField
                  name="iata"
                  label="IATA"
                  value={formData.iata || ''}
                  onChange={handleChange}
                  fullWidth
                />
              </Grid>
              <Grid xs={6}>
                <TextField
                  name="seudo_sabre"
                  label="Seudo SABRE"
                  value={formData.seudo_sabre || ''}
                  onChange={handleChange}
                  fullWidth
                />
              </Grid>
              <Grid xs={6}>
                <TextField
                  name="office_id_kiu"
                  label="Office ID KIU"
                  value={formData.office_id_kiu || ''}
                  onChange={handleChange}
                  fullWidth
                />
              </Grid>
              <Grid xs={6}>
                <TextField
                  name="office_id_amadeus"
                  label="Office ID AMADEUS"
                  value={formData.office_id_amadeus || ''}
                  onChange={handleChange}
                  fullWidth
                />
              </Grid>
              <Grid xs={6}>
                <TextField
                  name="office_id_travelport"
                  label="Office ID TRAVELPORT"
                  value={formData.office_id_travelport || ''}
                  onChange={handleChange}
                  fullWidth
                />
              </Grid>
              <Grid xs={6}>
                <TextField
                  name="office_id_hotelbeds"
                  label="Office ID HOTEL BEDS"
                  value={formData.office_id_hotelbeds || ''}
                  onChange={handleChange}
                  fullWidth
                />
              </Grid>
              <Grid xs={6}>
                <TextField
                  name="office_id_expedia"
                  label="Office ID EXPEDIA"
                  value={formData.office_id_expedia || ''}
                  onChange={handleChange}
                  fullWidth
                />
              </Grid>
            </Grid>
          </AccordionDetails>
        </Accordion>

        {/* Otros Sistemas */}
        <Accordion>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="subtitle1">Otros Sistemas de Reserva</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Grid container spacing={2}>
              {[1, 2, 3, 4, 5].map((num) => (
                <React.Fragment key={num}>
                  <Grid xs={6}>
                    <TextField
                      name={`otro_sistema_${num}_nombre`}
                      label={`Sistema ${num}: Nombre`}
                      value={formData[`otro_sistema_${num}_nombre` as keyof Proveedor] || ''}
                      onChange={handleChange}
                      fullWidth
                    />
                  </Grid>
                  <Grid xs={6}>
                    <TextField
                      name={`otro_sistema_${num}_id`}
                      label={`Sistema ${num}: ID`}
                      value={formData[`otro_sistema_${num}_id` as keyof Proveedor] || ''}
                      onChange={handleChange}
                      fullWidth
                    />
                  </Grid>
                </React.Fragment>
              ))}
            </Grid>
          </AccordionDetails>
        </Accordion>

        {/* Notas */}
        <Accordion>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="subtitle1">Notas</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <TextField
              name="notas"
              label="Notas sobre el Proveedor"
              value={formData.notas || ''}
              onChange={handleChange}
              fullWidth
              multiline
              rows={4}
            />
          </AccordionDetails>
        </Accordion>

        <Box sx={{ mt: 3, display: 'flex', justifyContent: 'flex-end' }}>
          <Button onClick={onClose} sx={{ mr: 1 }}>Cancelar</Button>
          <Button onClick={handleSave} variant="contained">Guardar</Button>
        </Box>
      </Box>
    </Modal>
  );
};

export default ProveedorForm;