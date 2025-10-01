'use client';

import React, { useState, useEffect } from 'react';
import { Modal, Box, Typography, Button, Grid, TextField, CircularProgress, Alert } from '@mui/material';
import { Factura } from '@/types/api';

const style = {
  position: 'absolute' as 'absolute',
  top: '50%',
  left: '50%',
  transform: 'translate(-50%, -50%)',
  width: '50%',
  bgcolor: 'background.paper',
  border: '2px solid #000',
  boxShadow: 24,
  p: 4,
  maxHeight: '90vh',
  overflowY: 'auto',
};

interface FacturaFormProps {
  open: boolean;
  onClose: () => void;
  onSave?: (factura: Partial<Factura>) => Promise<void>;
  factura: Partial<Factura> | null;
  readOnly?: boolean;
}

export default function FacturaForm({ open, onClose, onSave, factura, readOnly = false }: FacturaFormProps) {
  const [formData, setFormData] = useState<Partial<Factura>>(factura || {});
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      const initialData = factura ? {
        ...factura,
        fecha_emision: factura.fecha_emision ? factura.fecha_emision.split('T')[0] : new Date().toISOString().split('T')[0],
        fecha_vencimiento: factura.fecha_vencimiento ? factura.fecha_vencimiento.split('T')[0] : '',
      } : {
        fecha_emision: new Date().toISOString().split('T')[0],
      };
      setFormData(initialData);
      setError(null);
    }
  }, [factura, open]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSave = async () => {
    if (!onSave) return;
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
  
  const isNew = !factura?.id_factura;
  const title = readOnly ? `Detalles de Factura ${factura?.numero_factura}` : (isNew ? 'Crear Nueva Factura' : `Editar Factura ${factura?.numero_factura}`);

  return (
    <Modal open={open} onClose={onClose}>
      <Box sx={style}>
        <Typography variant="h6" component="h2" gutterBottom>
          {title}
        </Typography>
        <Grid container spacing={2} sx={{ mt: 2 }}>
          <Grid item xs={12} sm={6}>
            <TextField name="numero_factura" label="Número de Factura" value={formData.numero_factura || ''} onChange={handleChange} fullWidth helperText="Dejar en blanco para autogenerar" disabled={readOnly} />
          </Grid>
          <Grid item xs={12} sm={6}>
            <TextField label="Cliente (ID)" name="cliente" value={formData.cliente || ''} onChange={handleChange} fullWidth required disabled={readOnly} />
          </Grid>
          <Grid item xs={12} sm={6}>
            <TextField name="fecha_emision" label="Fecha de Emisión" type="date" value={formData.fecha_emision || ''} onChange={handleChange} fullWidth InputLabelProps={{ shrink: true }} required disabled={readOnly} />
          </Grid>
          <Grid item xs={12} sm={6}>
            <TextField name="fecha_vencimiento" label="Fecha de Vencimiento" type="date" value={formData.fecha_vencimiento || ''} onChange={handleChange} fullWidth InputLabelProps={{ shrink: true }} disabled={readOnly} />
          </Grid>
           <Grid item xs={12} sm={6}>
            <TextField label="Moneda (ID)" name="moneda" value={formData.moneda || ''} onChange={handleChange} fullWidth required disabled={readOnly} />
          </Grid>
          <Grid item xs={12} sm={6}>
            <TextField name="subtotal" label="Subtotal" type="number" value={formData.subtotal || ''} onChange={handleChange} fullWidth required disabled={readOnly} />
          </Grid>
          <Grid item xs={12}>
            <TextField name="notas" label="Notas" value={formData.notas || ''} onChange={handleChange} fullWidth multiline rows={3} disabled={readOnly} />
          </Grid>
        </Grid>
        
        {error && <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>}

        <Box sx={{ mt: 3, display: 'flex', justifyContent: 'flex-end', alignItems: 'center' }}>
          {readOnly ? (
            <Button onClick={onClose}>Cerrar</Button>
          ) : (
            <>
              {isSaving && <CircularProgress size={24} sx={{ mr: 2 }} />}
              <Button onClick={onClose} sx={{ mr: 1 }} disabled={isSaving}>Cancelar</Button>
              <Button onClick={handleSave} variant="contained" disabled={isSaving}>
                {isNew ? 'Crear Factura' : 'Guardar Cambios'}
              </Button>
            </>
          )}
        </Box>
      </Box>
    </Modal>
  );
}
