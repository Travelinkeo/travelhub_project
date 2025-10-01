'use client';

import React, { useEffect } from 'react';
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Dialog, DialogTitle, DialogContent, DialogActions, Button, TextField, Grid } from '@mui/material';
import { DatePicker } from '@mui/x-date-pickers';
import dayjs from 'dayjs';
import ApiAutocomplete from '@/components/forms/ApiAutocomplete';

const tourActividadSchema = z.object({
  nombre: z.string().min(1, 'El nombre del tour/actividad es requerido'),
  fecha: z.any().nullable(),
  duracion_horas: z.number().min(0.5, 'La duración debe ser al menos 0.5 horas').default(1),
  incluye: z.string().optional(),
  no_incluye: z.string().optional(),
  proveedor: z.number().optional().nullable(),
  notas: z.string().optional(),
});

type TourActividadFormData = z.infer<typeof tourActividadSchema>;

interface TourActividadFormProps {
  open: boolean;
  onClose: () => void;
  onSave: (data: TourActividadFormData) => void;
  tourActividad: Partial<TourActividadFormData> | null;
}

export default function TourActividadForm({ open, onClose, onSave, tourActividad }: TourActividadFormProps) {
  const { control, handleSubmit, reset, formState: { errors } } = useForm<TourActividadFormData>({
    resolver: zodResolver(tourActividadSchema),
    defaultValues: {
      nombre: '',
      fecha: null,
      duracion_horas: 1,
      incluye: '',
      no_incluye: '',
      proveedor: null,
      notas: '',
    },
  });

  useEffect(() => {
    if (open && tourActividad) {
      const valuesToReset = {
        ...tourActividad,
        fecha: tourActividad.fecha ? dayjs(tourActividad.fecha) : null,
      };
      reset(valuesToReset);
    } else if (open) {
      reset();
    }
  }, [tourActividad, open, reset]);

  const handleFormSubmit = (data: TourActividadFormData) => {
    const dataToSave = {
      ...data,
      fecha: data.fecha ? dayjs(data.fecha).format('YYYY-MM-DD') : null,
      proveedor: data.proveedor && data.proveedor > 0 ? data.proveedor : undefined,
    };
    onSave(dataToSave);
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        {tourActividad?.nombre ? 'Editar Tour/Actividad' : 'Añadir Tour/Actividad'}
      </DialogTitle>
      <form onSubmit={handleSubmit(handleFormSubmit)}>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12}>
              <Controller
                name="nombre"
                control={control}
                render={({ field }) => (
                  <TextField 
                    {...field} 
                    label="Nombre del Tour/Actividad" 
                    fullWidth 
                    error={!!errors.nombre} 
                    helperText={errors.nombre?.message} 
                  />
                )}
              />
            </Grid>
            <Grid item xs={6}>
              <Controller
                name="fecha"
                control={control}
                render={({ field }) => (
                  <DatePicker 
                    label="Fecha" 
                    {...field} 
                    value={field.value ? dayjs(field.value) : null} 
                    onChange={(date) => field.onChange(date)} 
                  />
                )}
              />
            </Grid>
            <Grid item xs={6}>
              <Controller
                name="duracion_horas"
                control={control}
                render={({ field }) => (
                  <TextField 
                    {...field} 
                    type="number" 
                    label="Duración (horas)" 
                    fullWidth 
                    error={!!errors.duracion_horas} 
                    helperText={errors.duracion_horas?.message}
                    inputProps={{ min: 0.5, step: 0.5 }}
                  />
                )}
              />
            </Grid>
            <Grid item xs={12}>
              <Controller
                name="incluye"
                control={control}
                render={({ field }) => (
                  <TextField 
                    {...field} 
                    label="Incluye" 
                    fullWidth 
                    multiline 
                    rows={2}
                    placeholder="Ej: Transporte, guía, almuerzo..."
                  />
                )}
              />
            </Grid>
            <Grid item xs={12}>
              <Controller
                name="no_incluye"
                control={control}
                render={({ field }) => (
                  <TextField 
                    {...field} 
                    label="No Incluye" 
                    fullWidth 
                    multiline 
                    rows={2}
                    placeholder="Ej: Bebidas, propinas, gastos personales..."
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