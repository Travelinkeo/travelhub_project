'use client';

import React, { useState, useEffect } from 'react';
import {
  Modal, Box, Typography, Button, Grid, TextField,
  CircularProgress, Alert, MenuItem, Divider
} from '@mui/material';

const style = {
  position: 'absolute' as 'absolute',
  top: '50%',
  left: '50%',
  transform: 'translate(-50%, -50%)',
  width: '80%',
  maxWidth: 1200,
  bgcolor: 'background.paper',
  border: '2px solid #000',
  boxShadow: 24,
  p: 4,
  maxHeight: '90vh',
  overflowY: 'auto',
};

interface FacturaConsolidadaFormProps {
  open: boolean;
  onClose: () => void;
  onSave?: (factura: any) => Promise<void>;
  factura: any | null;
  readOnly?: boolean;
}

export default function FacturaConsolidadaForm({
  open,
  onClose,
  onSave,
  factura,
  readOnly = false
}: FacturaConsolidadaFormProps) {
  const [formData, setFormData] = useState<any>({});
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      const initialData = factura ? {
        ...factura,
        fecha_emision: factura.fecha_emision?.split('T')[0] || new Date().toISOString().split('T')[0],
        fecha_vencimiento: factura.fecha_vencimiento?.split('T')[0] || '',
      } : {
        fecha_emision: new Date().toISOString().split('T')[0],
        tipo_operacion: 'VENTA_PROPIA',
        moneda_operacion: 'DIVISA',
        modalidad_emision: 'DIGITAL',
        estado: 'BOR',
        cliente_es_residente: true,
      };
      setFormData(initialData);
      setError(null);
    }
  }, [factura, open]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value, type } = e.target;
    setFormData((prev: any) => ({
      ...prev,
      [name]: type === 'number' ? parseFloat(value) || 0 : value
    }));
  };

  const handleSave = async () => {
    if (!onSave) return;
    setIsSaving(true);
    setError(null);
    try {
      await onSave(formData);
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Error desconocido');
    } finally {
      setIsSaving(false);
    }
  };

  const isNew = !factura?.id_factura;
  const title = readOnly
    ? `Detalles de Factura ${factura?.numero_factura}`
    : isNew
    ? 'Crear Nueva Factura'
    : `Editar Factura ${factura?.numero_factura}`;

  return (
    <Modal open={open} onClose={onClose}>
      <Box sx={style}>
        <Typography variant="h6" component="h2" gutterBottom>
          {title}
        </Typography>

        <Grid container spacing={2} sx={{ mt: 1 }}>
          <Grid item xs={12}>
            <Typography variant="subtitle1" fontWeight="bold">Información Básica</Typography>
            <Divider sx={{ mb: 2 }} />
          </Grid>

          <Grid item xs={12} sm={4}>
            <TextField
              name="numero_factura"
              label="Número de Factura"
              value={formData.numero_factura || ''}
              onChange={handleChange}
              fullWidth
              helperText="Autogenerado"
              disabled={readOnly}
            />
          </Grid>

          <Grid item xs={12} sm={4}>
            <TextField
              name="cliente"
              label="Cliente (ID)"
              type="number"
              value={formData.cliente || ''}
              onChange={handleChange}
              fullWidth
              required
              disabled={readOnly}
            />
          </Grid>

          <Grid item xs={12} sm={4}>
            <TextField
              name="moneda"
              label="Moneda (ID)"
              type="number"
              value={formData.moneda || ''}
              onChange={handleChange}
              fullWidth
              required
              disabled={readOnly}
            />
          </Grid>

          <Grid item xs={12} sm={6}>
            <TextField
              name="fecha_emision"
              label="Fecha de Emisión"
              type="date"
              value={formData.fecha_emision || ''}
              onChange={handleChange}
              fullWidth
              InputLabelProps={{ shrink: true }}
              required
              disabled={readOnly}
            />
          </Grid>

          <Grid item xs={12} sm={6}>
            <TextField
              name="tipo_operacion"
              label="Tipo de Operación"
              select
              value={formData.tipo_operacion || 'VENTA_PROPIA'}
              onChange={handleChange}
              fullWidth
              disabled={readOnly}
            >
              <MenuItem value="VENTA_PROPIA">Venta Propia</MenuItem>
              <MenuItem value="INTERMEDIACION">Intermediación</MenuItem>
            </TextField>
          </Grid>

          <Grid item xs={12}>
            <Typography variant="subtitle1" fontWeight="bold" sx={{ mt: 2 }}>
              Emisor (Agencia)
            </Typography>
            <Divider sx={{ mb: 2 }} />
          </Grid>

          <Grid item xs={12} sm={4}>
            <TextField
              name="emisor_rif"
              label="RIF"
              value={formData.emisor_rif || ''}
              onChange={handleChange}
              fullWidth
              required
              disabled={readOnly}
            />
          </Grid>

          <Grid item xs={12} sm={8}>
            <TextField
              name="emisor_razon_social"
              label="Razón Social"
              value={formData.emisor_razon_social || ''}
              onChange={handleChange}
              fullWidth
              required
              disabled={readOnly}
            />
          </Grid>

          <Grid item xs={12}>
            <Typography variant="subtitle1" fontWeight="bold" sx={{ mt: 2 }}>
              Bases Imponibles (USD)
            </Typography>
            <Divider sx={{ mb: 2 }} />
          </Grid>

          <Grid item xs={12} sm={4}>
            <TextField
              name="subtotal_base_gravada"
              label="Base Gravada"
              type="number"
              value={formData.subtotal_base_gravada || 0}
              onChange={handleChange}
              fullWidth
              inputProps={{ step: '0.01' }}
              disabled={readOnly}
            />
          </Grid>

          <Grid item xs={12} sm={4}>
            <TextField
              name="subtotal_exento"
              label="Base Exenta"
              type="number"
              value={formData.subtotal_exento || 0}
              onChange={handleChange}
              fullWidth
              inputProps={{ step: '0.01' }}
              disabled={readOnly}
            />
          </Grid>

          <Grid item xs={12} sm={4}>
            <TextField
              name="tasa_cambio_bcv"
              label="Tasa BCV"
              type="number"
              value={formData.tasa_cambio_bcv || ''}
              onChange={handleChange}
              fullWidth
              inputProps={{ step: '0.01' }}
              disabled={readOnly}
            />
          </Grid>

          <Grid item xs={12}>
            <TextField
              name="notas"
              label="Notas"
              value={formData.notas || ''}
              onChange={handleChange}
              fullWidth
              multiline
              rows={3}
              disabled={readOnly}
            />
          </Grid>
        </Grid>

        {error && <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>}

        <Box sx={{ mt: 3, display: 'flex', justifyContent: 'flex-end' }}>
          {readOnly ? (
            <Button onClick={onClose}>Cerrar</Button>
          ) : (
            <>
              {isSaving && <CircularProgress size={24} sx={{ mr: 2 }} />}
              <Button onClick={onClose} sx={{ mr: 1 }} disabled={isSaving}>
                Cancelar
              </Button>
              <Button onClick={handleSave} variant="contained" disabled={isSaving}>
                {isNew ? 'Crear' : 'Guardar'}
              </Button>
            </>
          )}
        </Box>
      </Box>
    </Modal>
  );
}
