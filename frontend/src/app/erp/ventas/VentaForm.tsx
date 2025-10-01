'use client';

import React, { useEffect } from 'react';
import { useForm, Controller } from 'react-hook-form';
import { Venta } from '@/types/api';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  CircularProgress,
  Grid,
} from '@mui/material';
import ApiAutocomplete from '@/components/forms/ApiAutocomplete';

interface VentaFormProps {
  open: boolean;
  onClose: () => void;
  onSave: (data: Partial<Venta>) => Promise<void>;
  venta?: Venta | null;
}

export default function VentaForm({ open, onClose, onSave, venta }: VentaFormProps) {
  const { handleSubmit, control, reset, formState: { isSubmitting, errors } } = useForm<Partial<Venta>>({
    defaultValues: {},
  });

  useEffect(() => {
    if (open) {
        if (venta) {
            // Editing an existing sale: pre-fill with its data
            reset({
                ...venta,
                cliente: venta.cliente, // Ensure relations are referenced by ID
                moneda: venta.moneda,
            });
        } else {
            // Creating a new sale: reset to default/empty values
            reset({
                descripcion_general: '',
                cliente: undefined,
                moneda: undefined,
                estado: 'PEN', // Default state
            });
        }
    }
  }, [venta, open, reset]);

  const onSubmit = async (data: Partial<Venta>) => {
    await onSave(data);
    onClose();
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>{venta ? `Editar Venta #${venta.id_venta}` : 'Crear Nueva Venta'}</DialogTitle>
      <form onSubmit={handleSubmit(onSubmit)}>
        <DialogContent>
          <Grid container spacing={2} sx={{ pt: 1 }}>
            <Grid item xs={12} sm={6}>
              <Controller
                name="cliente"
                control={control}
                rules={{ required: 'El cliente es obligatorio' }}
                render={({ field }) => (
                  <ApiAutocomplete
                    {...field}
                    endpoint="/api/clientes/"
                    label="Cliente"
                    optionIdField="id_cliente"
                    optionLabelField="get_nombre_completo"
                    onChange={(value) => field.onChange(value)}
                    error={!!errors.cliente}
                    helperText={errors.cliente?.message}
                  />
                )}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
                <Controller
                    name="moneda"
                    control={control}
                    rules={{ required: 'La moneda es obligatoria' }}
                    render={({ field }) => (
                        <ApiAutocomplete
                            {...field}
                            endpoint="/api/monedas/" // Assuming this endpoint exists from auto-registration
                            label="Moneda"
                            optionIdField="id_moneda"
                            optionLabelField="nombre"
                            onChange={(value) => field.onChange(value)}
                            error={!!errors.moneda}
                            helperText={errors.moneda?.message}
                            enableSearch={false}
                        />
                    )}
                />
            </Grid>
            <Grid item xs={12}>
                <Controller
                name="descripcion_general"
                control={control}
                render={({ field }) => <TextField {...field} label="Descripción General" fullWidth multiline rows={3} />}
                />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions sx={{ p: 3 }}>
          <Button onClick={onClose} color="secondary">Cancelar</Button>
          <Button type="submit" variant="contained" disabled={isSubmitting}>
            {isSubmitting ? <CircularProgress size={24} /> : 'Guardar'}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
}