'use client';

import React, { useEffect, useState } from 'react';
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Dialog, DialogTitle, DialogContent, DialogActions, Button, TextField, Grid, IconButton, Box, Typography } from '@mui/material';
import { DatePicker, TimePicker } from '@mui/x-date-pickers';
import dayjs from 'dayjs';
import ApiAutocomplete from '@/components/forms/ApiAutocomplete';
import QuickAddModal from '@/components/forms/QuickAddModal';
import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';
import { useFieldArray } from 'react-hook-form';

const trasladoItemSchema = z.object({
  origen: z.string().min(1, 'El origen es requerido'),
  destino: z.string().min(1, 'El destino es requerido'),
  fecha_hora: z.any().nullable(),
  hora: z.any().nullable(),
});

const trasladoSchema = z.object({
  traslados: z.array(trasladoItemSchema).min(1, 'Debe haber al menos un traslado'),
  pasajeros: z.number().min(1, 'Número de pasajeros requerido').default(1),
  proveedor: z.number().optional().nullable(),
  notas: z.string().optional(),
});

type TrasladoFormData = z.infer<typeof trasladoSchema>;

interface TrasladoFormProps {
  open: boolean;
  onClose: () => void;
  onSave: (data: TrasladoFormData) => void;
  traslado: Partial<TrasladoFormData> | null;
}

export default function TrasladoForm({ open, onClose, onSave, traslado }: TrasladoFormProps) {
  const [quickAddModal, setQuickAddModal] = useState<{open: boolean, type: 'proveedor' | null}>({open: false, type: null});
  
  const { control, handleSubmit, reset, setValue, formState: { errors } } = useForm<TrasladoFormData>({
    resolver: zodResolver(trasladoSchema),
    defaultValues: {
      traslados: [{ origen: '', destino: '', fecha_hora: null, hora: null }],
      pasajeros: 1,
      proveedor: null,
      notas: '',
    },
  });
  
  const { fields, append, remove } = useFieldArray({
    control,
    name: 'traslados'
  });

  useEffect(() => {
    if (open && traslado) {
      const valuesToReset = {
        ...traslado,
        traslados: traslado.traslados || [{ origen: '', destino: '', fecha_hora: null, hora: null }],
      };
      reset(valuesToReset);
    } else if (open) {
      reset();
    }
  }, [traslado, open, reset]);

  const handleFormSubmit = (data: TrasladoFormData) => {
    const dataToSave = {
      ...data,
      traslados: data.traslados.map(t => ({
        ...t,
        fecha_hora: t.fecha_hora ? dayjs(t.fecha_hora).format('YYYY-MM-DD') : null,
        hora: t.hora ? dayjs(t.hora).format('HH:mm') : null,
      })),
      proveedor: data.proveedor && data.proveedor > 0 ? data.proveedor : undefined,
    };
    onSave(dataToSave);
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        {traslado?.origen ? 'Editar Traslado' : 'Añadir Traslado'}
      </DialogTitle>
      <form onSubmit={handleSubmit(handleFormSubmit)}>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12}>
              <Typography variant="h6">Traslados</Typography>
              {fields.map((field, index) => (
                <Box key={field.id} sx={{ border: '1px solid #e0e0e0', borderRadius: 1, p: 2, mb: 2 }}>
                  <Grid container spacing={2} alignItems="center">
                    <Grid item xs={12} sm={3}>
                      <Controller
                        name={`traslados.${index}.origen`}
                        control={control}
                        render={({ field }) => (
                          <TextField 
                            {...field} 
                            label="Origen" 
                            fullWidth 
                            error={!!errors.traslados?.[index]?.origen} 
                            helperText={errors.traslados?.[index]?.origen?.message} 
                          />
                        )}
                      />
                    </Grid>
                    <Grid item xs={12} sm={3}>
                      <Controller
                        name={`traslados.${index}.destino`}
                        control={control}
                        render={({ field }) => (
                          <TextField 
                            {...field} 
                            label="Destino" 
                            fullWidth 
                            error={!!errors.traslados?.[index]?.destino} 
                            helperText={errors.traslados?.[index]?.destino?.message} 
                          />
                        )}
                      />
                    </Grid>
                    <Grid item xs={6} sm={2}>
                      <Controller
                        name={`traslados.${index}.fecha_hora`}
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
                    <Grid item xs={6} sm={2}>
                      <Controller
                        name={`traslados.${index}.hora`}
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
                    <Grid item xs={12} sm={2}>
                      <IconButton 
                        color="error" 
                        onClick={() => remove(index)}
                        disabled={fields.length === 1}
                      >
                        <DeleteIcon />
                      </IconButton>
                    </Grid>
                  </Grid>
                </Box>
              ))}
              <Button 
                startIcon={<AddIcon />} 
                onClick={() => append({ origen: '', destino: '', fecha_hora: null, hora: null })}
                variant="outlined"
              >
                Añadir Traslado
              </Button>
            </Grid>
            
            <Grid item xs={6}>
              <Controller
                name="pasajeros"
                control={control}
                render={({ field }) => (
                  <TextField 
                    {...field}
                    onChange={(e) => field.onChange(parseInt(e.target.value) || 1)}
                    type="number" 
                    label="Número de Pasajeros" 
                    fullWidth 
                    error={!!errors.pasajeros} 
                    helperText={errors.pasajeros?.message}
                    inputProps={{ min: 1 }}
                  />
                )}
              />
            </Grid>
            <Grid item xs={6}>
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
                        label="Proveedor"
                        optionIdField="id_proveedor"
                        optionLabelField="nombre"
                        enableSearch={true}
                        error={!!errors.proveedor}
                        helperText={errors.proveedor?.message}
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
      
      <QuickAddModal
        open={quickAddModal.open}
        type={quickAddModal.type!}
        onClose={() => setQuickAddModal({open: false, type: null})}
        onSuccess={(newItem) => {
          setValue('proveedor', newItem.id_proveedor);
          setQuickAddModal({open: false, type: null});
        }}
      />
    </Dialog>
  );
}