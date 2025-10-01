'use client';

import React, { useEffect } from 'react';
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Dialog, DialogTitle, DialogContent, DialogActions, Button, TextField, Grid, MenuItem } from '@mui/material';
import { DatePicker, TimePicker } from '@mui/x-date-pickers';
import dayjs from 'dayjs';
import ApiAutocomplete from '@/components/forms/ApiAutocomplete';

const servicioAdicionalSchema = z.object({
  tipo_servicio: z.string().min(1, 'El tipo de servicio es requerido'),
  descripcion: z.string().min(1, 'La descripción es requerida'),
  lugar: z.string().optional(),
  fecha: z.any().nullable(),
  hora: z.any().nullable(),
  duracion_horas: z.number().optional(),
  pasajeros: z.number().optional(),
  destino: z.string().optional(),
  fecha_salida: z.any().nullable(),
  fecha_retorno: z.any().nullable(),
  proveedor: z.number().optional().nullable(),
  notas: z.string().optional(),
});

type ServicioAdicionalFormData = z.infer<typeof servicioAdicionalSchema>;

interface ServicioAdicionalFormProps {
  open: boolean;
  onClose: () => void;
  onSave: (data: ServicioAdicionalFormData) => void;
  servicioAdicional: Partial<ServicioAdicionalFormData> | null;
}

const tiposServicio = [
  'Asistencia',
  'SIM / E-SIM',
  'Lounge',
  'Otro'
];

export default function ServicioAdicionalForm({ open, onClose, onSave, servicioAdicional }: ServicioAdicionalFormProps) {
  const { control, handleSubmit, reset, watch, formState: { errors } } = useForm<ServicioAdicionalFormData>({
    resolver: zodResolver(servicioAdicionalSchema),
    defaultValues: {
      tipo_servicio: '',
      descripcion: '',
      lugar: '',
      fecha: null,
      hora: null,
      duracion_horas: undefined,
      pasajeros: undefined,
      destino: '',
      fecha_salida: null,
      fecha_retorno: null,
      proveedor: null,
      notas: '',
    },
  });

  const tipoServicio = watch('tipo_servicio');

  useEffect(() => {
    if (open && servicioAdicional) {
      const valuesToReset = {
        ...servicioAdicional,
        fecha: servicioAdicional.fecha ? dayjs(servicioAdicional.fecha) : null,
        hora: servicioAdicional.hora ? dayjs(servicioAdicional.hora, 'HH:mm') : null,
        fecha_salida: servicioAdicional.fecha_salida ? dayjs(servicioAdicional.fecha_salida) : null,
        fecha_retorno: servicioAdicional.fecha_retorno ? dayjs(servicioAdicional.fecha_retorno) : null,
      };
      reset(valuesToReset);
    } else if (open) {
      reset();
    }
  }, [servicioAdicional, open, reset]);

  const handleFormSubmit = (data: ServicioAdicionalFormData) => {
    const dataToSave = {
      ...data,
      fecha: data.fecha ? dayjs(data.fecha).format('YYYY-MM-DD') : null,
      hora: data.hora ? dayjs(data.hora).format('HH:mm') : null,
      fecha_salida: data.fecha_salida ? dayjs(data.fecha_salida).format('YYYY-MM-DD') : null,
      fecha_retorno: data.fecha_retorno ? dayjs(data.fecha_retorno).format('YYYY-MM-DD') : null,
      proveedor: data.proveedor && data.proveedor > 0 ? data.proveedor : undefined,
    };
    onSave(dataToSave);
  };

  const renderConditionalFields = () => {
    switch (tipoServicio) {
      case 'Asistencia':
        return (
          <>
            <Grid item xs={12} sm={6}>
              <Controller
                name="lugar"
                control={control}
                render={({ field }) => (
                  <TextField {...field} label="Lugar" fullWidth />
                )}
              />
            </Grid>
            <Grid item xs={6} sm={3}>
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
            <Grid item xs={6} sm={3}>
              <Controller
                name="hora"
                control={control}
                render={({ field }) => (
                  <TimePicker 
                    label="Hora" 
                    {...field} 
                    value={field.value ? dayjs(field.value, 'HH:mm') : null} 
                    onChange={(time) => field.onChange(time)} 
                  />
                )}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <Controller
                name="pasajeros"
                control={control}
                render={({ field }) => (
                  <TextField 
                    {...field} 
                    type="number" 
                    label="Número de Pasajeros" 
                    fullWidth 
                    inputProps={{ min: 1 }}
                  />
                )}
              />
            </Grid>
          </>
        );
      
      case 'SIM / E-SIM':
        return (
          <>
            <Grid item xs={12} sm={4}>
              <Controller
                name="destino"
                control={control}
                render={({ field }) => (
                  <TextField {...field} label="Destino" fullWidth />
                )}
              />
            </Grid>
            <Grid item xs={6} sm={4}>
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
            <Grid item xs={6} sm={4}>
              <Controller
                name="fecha_retorno"
                control={control}
                render={({ field }) => (
                  <DatePicker 
                    label="Fecha de Retorno" 
                    {...field} 
                    value={field.value ? dayjs(field.value) : null} 
                    onChange={(date) => field.onChange(date)} 
                  />
                )}
              />
            </Grid>
          </>
        );
      
      case 'Lounge':
        return (
          <>
            <Grid item xs={12} sm={6}>
              <Controller
                name="lugar"
                control={control}
                render={({ field }) => (
                  <TextField {...field} label="Nombre del Lounge" fullWidth />
                )}
              />
            </Grid>
            <Grid item xs={6} sm={2}>
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
            <Grid item xs={6} sm={4}>
              <Controller
                name="duracion_horas"
                control={control}
                render={({ field }) => (
                  <TextField 
                    {...field} 
                    type="number" 
                    label="Duración (horas)" 
                    fullWidth 
                    inputProps={{ min: 0.5, step: 0.5 }}
                  />
                )}
              />
            </Grid>
          </>
        );
      
      default:
        return (
          <Grid item xs={12}>
            <Controller
              name="lugar"
              control={control}
              render={({ field }) => (
                <TextField {...field} label="Detalles adicionales" fullWidth />
              )}
            />
          </Grid>
        );
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        {servicioAdicional?.tipo_servicio ? 'Editar Servicio Adicional' : 'Añadir Servicio Adicional'}
      </DialogTitle>
      <form onSubmit={handleSubmit(handleFormSubmit)}>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12} sm={6}>
              <Controller
                name="tipo_servicio"
                control={control}
                render={({ field }) => (
                  <TextField
                    {...field}
                    select
                    label="Tipo de Servicio"
                    fullWidth
                    error={!!errors.tipo_servicio}
                    helperText={errors.tipo_servicio?.message}
                  >
                    {tiposServicio.map((tipo) => (
                      <MenuItem key={tipo} value={tipo}>
                        {tipo}
                      </MenuItem>
                    ))}
                  </TextField>
                )}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <Controller
                name="descripcion"
                control={control}
                render={({ field }) => (
                  <TextField 
                    {...field} 
                    label="Descripción" 
                    fullWidth 
                    error={!!errors.descripcion} 
                    helperText={errors.descripcion?.message} 
                  />
                )}
              />
            </Grid>
            
            {renderConditionalFields()}
            
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