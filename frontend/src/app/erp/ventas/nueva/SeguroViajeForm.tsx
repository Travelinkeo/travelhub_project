'use client';

import React, { useEffect } from 'react';
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Dialog, DialogTitle, DialogContent, DialogActions, Button, TextField, Grid } from '@mui/material';
import { DatePicker } from '@mui/x-date-pickers';
import dayjs from 'dayjs';
import ApiAutocomplete from '@/components/forms/ApiAutocomplete';

const seguroViajeSchema = z.object({
  fecha_salida: z.any().nullable(),
  fecha_regreso: z.any().nullable(),
  plan: z.string().min(1, 'El plan es requerido'),
  cobertura_monto: z.number().min(1, 'El monto de cobertura es requerido'),
  proveedor: z.number().optional().nullable(),
  notas: z.string().optional(),
});

type SeguroViajeFormData = z.infer<typeof seguroViajeSchema>;

interface SeguroViajeFormProps {
  open: boolean;
  onClose: () => void;
  onSave: (data: SeguroViajeFormData) => void;
  seguroViaje: Partial<SeguroViajeFormData> | null;
}

export default function SeguroViajeForm({ open, onClose, onSave, seguroViaje }: SeguroViajeFormProps) {
  const { control, handleSubmit, reset, formState: { errors } } = useForm<SeguroViajeFormData>({
    resolver: zodResolver(seguroViajeSchema),
    defaultValues: {
      fecha_salida: null,
      fecha_regreso: null,
      plan: '',
      cobertura_monto: 0,
      proveedor: null,
      notas: '',
    },
  });

  useEffect(() => {
    if (open && seguroViaje) {
      const valuesToReset = {
        ...seguroViaje,
        fecha_salida: seguroViaje.fecha_salida ? dayjs(seguroViaje.fecha_salida) : null,
        fecha_regreso: seguroViaje.fecha_regreso ? dayjs(seguroViaje.fecha_regreso) : null,
      };
      reset(valuesToReset);
    } else if (open) {
      reset();
    }
  }, [seguroViaje, open, reset]);

  const handleFormSubmit = (data: SeguroViajeFormData) => {
    const dataToSave = {
      ...data,
      fecha_salida: data.fecha_salida ? dayjs(data.fecha_salida).format('YYYY-MM-DD') : null,
      fecha_regreso: data.fecha_regreso ? dayjs(data.fecha_regreso).format('YYYY-MM-DD') : null,
      proveedor: data.proveedor && data.proveedor > 0 ? data.proveedor : undefined,
    };
    onSave(dataToSave);
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        {seguroViaje?.plan ? 'Editar Seguro de Viaje' : 'Añadir Seguro de Viaje'}
      </DialogTitle>
      <form onSubmit={handleSubmit(handleFormSubmit)}>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={6}>
              <Controller
                name="fecha_salida"
                control={control}
                render={({ field }) => (
                  <DatePicker 
                    label="Fecha de Salida" 
                    {...field} 
                    value={field.value ? dayjs(field.value) : null} 
                    onChange={(date) => field.onChange(date)} 
                  />
                )}
              />
            </Grid>
            <Grid item xs={6}>
              <Controller
                name="fecha_regreso"
                control={control}
                render={({ field }) => (
                  <DatePicker 
                    label="Fecha de Regreso" 
                    {...field} 
                    value={field.value ? dayjs(field.value) : null} 
                    onChange={(date) => field.onChange(date)} 
                  />
                )}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <Controller
                name="plan"
                control={control}
                render={({ field }) => (
                  <TextField 
                    {...field} 
                    label="Plan de Seguro" 
                    fullWidth 
                    error={!!errors.plan} 
                    helperText={errors.plan?.message}
                    placeholder="Ej: Plan Básico, Plan Premium, Plan Familiar..."
                  />
                )}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <Controller
                name="cobertura_monto"
                control={control}
                render={({ field }) => (
                  <TextField 
                    {...field}
                    onChange={(e) => field.onChange(parseFloat(e.target.value) || 0)}
                    type="number" 
                    label="Cobertura (Monto USD)" 
                    fullWidth 
                    error={!!errors.cobertura_monto} 
                    helperText={errors.cobertura_monto?.message}
                    inputProps={{ min: 1, step: "0.01" }}
                  />
                )}
              />
            </Grid>
            <Grid item xs={12}>
              <Controller
                name="proveedor"
                control={control}
                render={({ field }) => (
                  <ApiAutocomplete
                    value={field.value}
                    onChange={field.onChange}
                    endpoint="/api/proveedores/"
                    label="Proveedor"
                    optionIdField="id_proveedor"
                    optionLabelField="nombre"
                    enableSearch={true}
                    error={!!errors.proveedor}
                    helperText={errors.proveedor?.message}
                  />
                )}
              />
            </Grid>
            <Grid item xs={12}>
              <Controller
                name="notas"
                control={control}
                render={({ field }) => (
                  <TextField {...field} label="Notas y Observaciones" fullWidth multiline rows={3} />
                )}
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose}>Cancelar</Button>
          <Button type="submit" variant="contained">Guardar</Button>
        </DialogActions>
      </form>
    </Dialog>
  );
}