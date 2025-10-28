'use client';

import React, { useEffect, useState } from 'react';
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Dialog, DialogTitle, DialogContent, DialogActions, Button, TextField, Grid, Autocomplete } from '@mui/material';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import dayjs from 'dayjs';
import ApiAutocomplete from '@/components/forms/ApiAutocomplete';
import QuickAddModal from '@/components/forms/QuickAddModal';
import { useApi } from '@/hooks/useApi';
import { useDebounce } from '@/hooks/useDebounce';
import AddIcon from '@mui/icons-material/Add';
import { IconButton, Box } from '@mui/material';



// Zod Schema for Alojamiento
const alojamientoSchema = z.object({
  nombre_establecimiento: z.string().min(1, 'El nombre es requerido'),
  ciudad: z.number().min(1, "La ciudad es requerida").nullable(),
  check_in: z.any().nullable(),
  check_out: z.any().nullable(),
  regimen_alimentacion: z.string().optional(),
  habitaciones: z.number().min(1).default(1),
  proveedor: z.number().optional().nullable(),
  notas: z.string().optional(),
});

type AlojamientoFormData = z.infer<typeof alojamientoSchema>;

interface AlojamientoFormProps {
  open: boolean;
  onClose: () => void;
  onSave: (data: AlojamientoFormData) => void;
  alojamiento: Partial<AlojamientoFormData> | null;
}

export default function AlojamientoForm({ open, onClose, onSave, alojamiento }: AlojamientoFormProps) {
  const [quickAddModal, setQuickAddModal] = useState<{open: boolean, type: 'cliente' | 'proveedor' | 'ciudad' | null}>({open: false, type: null});
  
  const { control, handleSubmit, reset, setValue, formState: { errors } } = useForm<AlojamientoFormData>({
    resolver: zodResolver(alojamientoSchema),
    defaultValues: {
      nombre_establecimiento: '',
      ciudad: null,
      check_in: null,
      check_out: null,
      regimen_alimentacion: '',
      habitaciones: 1,
      proveedor: null,
      notas: '',
    },
  });

  useEffect(() => {
    if (open && alojamiento) {
      const valuesToReset = {
        ...alojamiento,
        check_in: alojamiento.check_in ? dayjs(alojamiento.check_in) : null,
        check_out: alojamiento.check_out ? dayjs(alojamiento.check_out) : null,
      };
      reset(valuesToReset);
    } else if (open) {
      reset(); // Reset to default values when creating new
    }
  }, [alojamiento, open, reset]);

  const handleFormSubmit = (data: AlojamientoFormData) => {
    // Convert dayjs objects to YYYY-MM-DD format for API
    const dataToSave = {
        ...data,
        check_in: data.check_in ? dayjs(data.check_in).format('YYYY-MM-DD') : null,
        check_out: data.check_out ? dayjs(data.check_out).format('YYYY-MM-DD') : null,
        // Solo incluir proveedor si tiene un valor válido
        proveedor: data.proveedor && data.proveedor > 0 ? data.proveedor : undefined,
    };
    onSave(dataToSave);
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>{alojamiento?.nombre_establecimiento ? 'Editar Detalles de Alojamiento' : 'Añadir Detalles de Alojamiento'}</DialogTitle>
      <form onSubmit={handleSubmit(handleFormSubmit)}>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12} sm={6}>
              <Controller
                name="nombre_establecimiento"
                control={control}
                render={({ field }) => <TextField {...field} label="Nombre del Hotel/Posada" fullWidth error={!!errors.nombre_establecimiento} helperText={errors.nombre_establecimiento?.message} />}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Box sx={{ flexGrow: 1 }}>
                        <Controller
                            name="ciudad"
                            control={control}
                            render={({ field }) => (
                                <ApiAutocomplete
                                    value={field.value}
                                    onChange={field.onChange}
                                    endpoint="/api/ciudades/"
                                    label="Ciudad"
                                    optionIdField="id_ciudad"
                                    optionLabelField="nombre"
                                    enableSearch={true}
                                    error={!!errors.ciudad}
                                    helperText={errors.ciudad?.message}
                                    getOptionLabel={(option: any) => option ? `${option.nombre} - ${option.pais_detalle?.nombre || ''}` : ''}
                                />
                            )}
                        />
                    </Box>
                    <IconButton 
                        color="primary" 
                        onClick={() => setQuickAddModal({open: true, type: 'ciudad'})}
                        title="Añadir nueva ciudad"
                    >
                        <AddIcon />
                    </IconButton>
                </Box>
            </Grid>
            <Grid item xs={6}>
              <Controller
                name="check_in"
                control={control}
                render={({ field }) => <DatePicker label="Check In" {...field} value={field.value ? dayjs(field.value) : null} onChange={(date) => field.onChange(date)} />}
              />
            </Grid>
            <Grid item xs={6}>
              <Controller
                name="check_out"
                control={control}
                render={({ field }) => <DatePicker label="Check Out" {...field} value={field.value ? dayjs(field.value) : null} onChange={(date) => field.onChange(date)} />}
              />
            </Grid>
            <Grid item xs={4}>
              <Controller
                name="regimen_alimentacion"
                control={control}
                render={({ field }) => <TextField {...field} label="Régimen de Alimentación" fullWidth />}
              />
            </Grid>
            <Grid item xs={4}>
              <Controller
                name="habitaciones"
                control={control}
                render={({ field }) => <TextField {...field} type="number" label="Cantidad de Habitaciones" fullWidth />}
              />
            </Grid>
            <Grid item xs={4}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Box sx={{ flexGrow: 1 }}>
                  <Controller
                    name="proveedor"
                    control={control}
                    render={({ field }) => (
                      <ApiAutocomplete
                        value={field.value}
                        onChange={field.onChange}
                        endpoint="/api/proveedores/"
                        label="Proveedor (opcional)"
                        optionIdField="id_proveedor"
                        optionLabelField="nombre"
                        enableSearch={true}
                      />
                    )}
                  />
                </Box>
                <IconButton 
                  color="primary" 
                  onClick={() => setQuickAddModal({open: true, type: 'proveedor'})}
                  title="Añadir nuevo proveedor"
                >
                  <AddIcon />
                </IconButton>
              </Box>
            </Grid>
            <Grid item xs={12}>
              <Controller
                name="notas"
                control={control}
                render={({ field }) => <TextField {...field} label="Notas" fullWidth multiline rows={3} />}
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose}>Cancelar</Button>
          <Button type="submit" variant="contained">Guardar Detalles</Button>
        </DialogActions>
      </form>
      
      <QuickAddModal
        open={quickAddModal.open}
        type={quickAddModal.type!}
        onClose={() => setQuickAddModal({open: false, type: null})}
        onSuccess={(newItem) => {
          if (quickAddModal.type === 'ciudad') {
            setValue('ciudad', newItem.id_ciudad);
          } else if (quickAddModal.type === 'proveedor') {
            setValue('proveedor', newItem.id_proveedor);
          }
          setQuickAddModal({open: false, type: null});
        }}
      />
    </Dialog>
  );
}
