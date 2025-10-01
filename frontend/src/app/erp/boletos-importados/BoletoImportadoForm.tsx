'use client';

import React, { useState, useEffect } from 'react';
import { Modal, Box, Typography, Button, CircularProgress, Alert } from '@mui/material';
import Grid from '@mui/material/Grid';
import TextField from '@mui/material/TextField';
import { BoletoImportado } from '@/types/api';

const style = {
  position: 'absolute' as 'absolute',
  top: '50%',
  left: '50%',
  transform: 'translate(-50%, -50%)',
  width: '60%',
  bgcolor: 'background.paper',
  border: '2px solid #000',
  boxShadow: 24,
  p: 4,
  maxHeight: '90vh',
  overflowY: 'auto',
};

interface BoletoFormProps {
  open: boolean;
  onClose: () => void;
  onSave?: (boleto: Partial<BoletoImportado>) => Promise<void>; // onSave is optional now
  boleto: BoletoImportado | null;
  readOnly?: boolean; // Step 1: Add readOnly prop
}

export default function BoletoImportadoForm({ open, onClose, onSave, boleto, readOnly = false }: BoletoFormProps) {
  const [formData, setFormData] = useState<Partial<BoletoImportado>>(boleto || {});
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      const initialData = boleto ? {
        ...boleto,
        fecha_emision_boleto: boleto.fecha_emision_boleto ? boleto.fecha_emision_boleto.split('T')[0] : '',
      } : {};
      setFormData(initialData);
      setError(null);
    }
  }, [boleto, open]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSave = async () => {
    if (!onSave) return; // Type guard
    setIsSaving(true);
    setError(null);
    try {
      await onSave(formData);
      onClose();
    } catch (e) {
      const errorMessage = e instanceof Error ? e.message : 'Ocurrió un error desconocido.';
      setError(errorMessage);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <Modal open={open} onClose={onClose}>
      <Box sx={style}>
        <Typography variant="h6" component="h2" gutterBottom>
          {/* Step 2: Change title based on mode */}
          {readOnly ? 'Detalles del Boleto' : 'Editar Boleto'} (ID: {boleto?.id_boleto_importado})
        </Typography>
        <Grid container spacing={2} sx={{ mt: 2 }}>
          {/* Step 3: Disable all fields if readOnly */}
          <Grid item xs={12} sm={6}>
            <TextField name="localizador_pnr" label="Localizador (PNR)" value={formData.localizador_pnr || ''} onChange={handleChange} fullWidth disabled={readOnly} />
          </Grid>
          <Grid item xs={12} sm={6}>
            <TextField name="numero_boleto" label="Número de Boleto" value={formData.numero_boleto || ''} onChange={handleChange} fullWidth disabled={readOnly} />
          </Grid>
          <Grid item xs={12}>
            <TextField name="nombre_pasajero_procesado" label="Nombre Pasajero" value={formData.nombre_pasajero_procesado || ''} onChange={handleChange} fullWidth disabled={readOnly} />
          </Grid>
          <Grid item xs={12} sm={6}>
            <TextField name="aerolinea_emisora" label="Aerolínea Emisora" value={formData.aerolinea_emisora || ''} onChange={handleChange} fullWidth disabled={readOnly} />
          </Grid>
           <Grid item xs={12} sm={6}>
            <TextField name="fecha_emision_boleto" label="Fecha Emisión" type="date" value={formData.fecha_emision_boleto || ''} onChange={handleChange} fullWidth InputLabelProps={{ shrink: true }} disabled={readOnly} />
          </Grid>
          <Grid item xs={12} sm={4}>
            <TextField name="total_boleto" label="Total Boleto" type="number" value={formData.total_boleto || ''} onChange={handleChange} fullWidth disabled={readOnly} />
          </Grid>
          <Grid item xs={12} sm={4}>
            <TextField name="fee_servicio" label="Fee Servicio" type="number" value={formData.fee_servicio || ''} onChange={handleChange} fullWidth disabled={readOnly} />
          </Grid>
           <Grid item xs={12} sm={4}>
            <TextField name="comision_agencia" label="Comisión Agencia" type="number" value={formData.comision_agencia || ''} onChange={handleChange} fullWidth disabled={readOnly} />
          </Grid>
        </Grid>
        
        {error && <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>}

        <Box sx={{ mt: 3, display: 'flex', justifyContent: 'flex-end', alignItems: 'center' }}>
          {/* Step 4: Change buttons based on mode */}
          {readOnly ? (
            <Button onClick={onClose}>Cerrar</Button>
          ) : (
            <>
              {isSaving && <CircularProgress size={24} sx={{ mr: 2 }} />}
              <Button onClick={onClose} sx={{ mr: 1 }} disabled={isSaving}>Cancelar</Button>
              <Button onClick={handleSave} variant="contained" disabled={isSaving}>
                Guardar Cambios
              </Button>
            </>
          )}
        </Box>
      </Box>
    </Modal>
  );
}