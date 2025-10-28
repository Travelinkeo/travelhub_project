'use client';

import React, { useEffect } from 'react';
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Dialog, DialogTitle, DialogContent, DialogActions, Button, TextField, Grid, Autocomplete, FormControlLabel, Checkbox, MenuItem } from '@mui/material';
import { DatePicker, TimePicker } from '@mui/x-date-pickers';
import dayjs from 'dayjs';
import ApiAutocomplete from '@/components/forms/ApiAutocomplete';


const CiudadAutocomplete = ({ value, onChange, error, helperText, label }: any) => {
  return (
    <ApiAutocomplete
      value={value}
      onChange={onChange}
      endpoint="/api/ciudades/"
      label={label}
      optionIdField="id_ciudad"
      optionLabelField="nombre"
      enableSearch={true}
      error={error}
      helperText={helperText}
    />
  );
};

const alquilerAutoSchema = z.object({
  compania_rentadora: z.string().min(1, 'La compañía es requerida'),
  categoria_auto: z.string().min(1, 'La categoría es requerida'),
  fecha_recogida: z.any().nullable(),
  hora_recogida: z.any().nullable(),
  fecha_devolucion: z.any().nullable(),
  hora_devolucion: z.any().nullable(),
  ciudad_retiro: z.number().min(1, 'Ciudad de recogida requerida').nullable(),
  ciudad_devolucion: z.number().min(1, 'Ciudad de devolución requerida').nullable(),
  incluye_seguro: z.boolean().default(false),
  numero_confirmacion: z.string().optional(),
  proveedor: z.number().optional().nullable(),
  notas: z.string().optional(),
});

type AlquilerAutoFormData = z.infer<typeof alquilerAutoSchema>;

interface AlquilerAutoFormProps {
  open: boolean;
  onClose: () => void;
  onSave: (data: AlquilerAutoFormData) => void;
  alquilerAuto: Partial<AlquilerAutoFormData> | null;
}

const categorias = [
  'Compacto', 'Mini', 'Económico', 'Standard', 'SUV', 'Premium', 'Lujo', 'Camioneta', 'Todo Terreno'
];

export default function AlquilerAutoForm({ open, onClose, onSave, alquilerAuto }: AlquilerAutoFormProps) {
  const { control, handleSubmit, reset, formState: { errors } } = useForm<AlquilerAutoFormData>({
    resolver: zodResolver(alquilerAutoSchema),
    defaultValues: {
      compania_rentadora: '',
      categoria_auto: '',
      fecha_recogida: null,
      hora_recogida: null,
      fecha_devolucion: null,
      hora_devolucion: null,
      ciudad_retiro: null,
      ciudad_devolucion: null,
      incluye_seguro: false,
      numero_confirmacion: '',
      proveedor: null,
      notas: '',
    },
  });

  useEffect(() => {
    if (open && alquilerAuto) {
      const valuesToReset = {
        ...alquilerAuto,
        fecha_recogida: alquilerAuto.fecha_recogida ? dayjs(alquilerAuto.fecha_recogida) : null,
        hora_recogida: alquilerAuto.hora_recogida ? dayjs(alquilerAuto.hora_recogida, 'HH:mm') : null,
        fecha_devolucion: alquilerAuto.fecha_devolucion ? dayjs(alquilerAuto.fecha_devolucion) : null,
        hora_devolucion: alquilerAuto.hora_devolucion ? dayjs(alquilerAuto.hora_devolucion, 'HH:mm') : null,
      };
      reset(valuesToReset);
    } else if (open) {
      reset();
    }
  }, [alquilerAuto, open, reset]);

  const handleFormSubmit = (data: AlquilerAutoFormData) => {
    const dataToSave = {
      ...data,
      fecha_recogida: data.fecha_recogida ? dayjs(data.fecha_recogida).format('YYYY-MM-DD') : null,
      hora_recogida: data.hora_recogida ? dayjs(data.hora_recogida).format('HH:mm') : null,
      fecha_devolucion: data.fecha_devolucion ? dayjs(data.fecha_devolucion).format('YYYY-MM-DD') : null,
      hora_devolucion: data.hora_devolucion ? dayjs(data.hora_devolucion).format('HH:mm') : null,
      proveedor: data.proveedor && data.proveedor > 0 ? data.proveedor : undefined,
    };
    onSave(dataToSave);
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="lg" fullWidth>
      <DialogTitle>
        {alquilerAuto?.compania_rentadora ? 'Editar Alquiler de Auto' : 'Añadir Alquiler de Auto'}
      </DialogTitle>
      <form onSubmit={handleSubmit(handleFormSubmit)}>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12} sm={6}>
              <Controller
                name="compania_rentadora"
                control={control}
                render={({ field }) => (
                  <TextField 
                    {...field} 
                    label="Compañía Arrendadora" 
                    fullWidth 
                    error={!!errors.compania_rentadora} 
                    helperText={errors.compania_rentadora?.message} 
                  />
                )}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <Controller
                name="categoria_auto"
                control={control}
                render={({ field }) => (
                  <TextField
                    {...field}
                    select
                    label="Categoría del Auto"
                    fullWidth
                    error={!!errors.categoria_auto}
                    helperText={errors.categoria_auto?.message}
                  >
                    {categorias.map((categoria) => (
                      <MenuItem key={categoria} value={categoria}>
                        {categoria}
                      </MenuItem>
                    ))}
                  </TextField>
                )}
              />
            </Grid>
            <Grid item xs={6} sm={3}>
              <Controller
                name="fecha_recogida"
                control={control}
                render={({ field }) => (
                  <DatePicker 
                    label="Fecha Recogida" 
                    {...field} 
                    value={field.value ? dayjs(field.value) : null} 
                    onChange={(date) => field.onChange(date)} 
                  />
                )}
              />
            </Grid>
            <Grid item xs={6} sm={3}>
              <Controller
                name="hora_recogida"
                control={control}
                render={({ field }) => (
                  <TimePicker 
                    label="Hora Recogida" 
                    {...field} 
                    value={field.value ? dayjs(field.value, 'HH:mm') : null} 
                    onChange={(time) => field.onChange(time)} 
                  />
                )}
              />
            </Grid>
            <Grid item xs={6} sm={3}>
              <Controller
                name="fecha_devolucion"
                control={control}
                render={({ field }) => (
                  <DatePicker 
                    label="Fecha Devolución" 
                    {...field} 
                    value={field.value ? dayjs(field.value) : null} 
                    onChange={(date) => field.onChange(date)} 
                  />
                )}
              />
            </Grid>
            <Grid item xs={6} sm={3}>
              <Controller
                name="hora_devolucion"
                control={control}
                render={({ field }) => (
                  <TimePicker 
                    label="Hora Devolución" 
                    {...field} 
                    value={field.value ? dayjs(field.value, 'HH:mm') : null} 
                    onChange={(time) => field.onChange(time)} 
                  />
                )}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <Controller
                name="ciudad_retiro"
                control={control}
                render={({ field }) => (
                  <CiudadAutocomplete
                    value={field.value || null}
                    onChange={field.onChange}
                    error={!!errors.ciudad_retiro}
                    helperText={errors.ciudad_retiro?.message}
                    label="Ciudad de Recogida"
                  />
                )}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <Controller
                name="ciudad_devolucion"
                control={control}
                render={({ field }) => (
                  <CiudadAutocomplete
                    value={field.value || null}
                    onChange={field.onChange}
                    error={!!errors.ciudad_devolucion}
                    helperText={errors.ciudad_devolucion?.message}
                    label="Ciudad de Devolución"
                  />
                )}
              />
            </Grid>
            <Grid item xs={12} sm={4}>
              <Controller
                name="incluye_seguro"
                control={control}
                render={({ field }) => (
                  <FormControlLabel
                    control={<Checkbox {...field} checked={field.value} />}
                    label="¿Incluye Seguro?"
                  />
                )}
              />
            </Grid>
            <Grid item xs={12} sm={4}>
              <Controller
                name="numero_confirmacion"
                control={control}
                render={({ field }) => (
                  <TextField {...field} label="Número de Confirmación" fullWidth />
                )}
              />
            </Grid>
            <Grid item xs={12} sm={4}>
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