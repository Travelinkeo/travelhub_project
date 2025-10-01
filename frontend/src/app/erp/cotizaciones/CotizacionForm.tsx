'use client';

import React, { useState, useEffect } from 'react';
import { useForm, Controller, useFieldArray } from 'react-hook-form';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
  Grid,
  Box,
  IconButton,
  Typography,
  MenuItem,
  Select,
  FormControl,
  InputLabel
} from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import EditIcon from '@mui/icons-material/Edit';
import { Cotizacion, ItemCotizacion, Cliente, User, TipoItemCotizacion } from '@/types/api';
import ItemDetallesForm from './ItemDetallesForm';

interface CotizacionFormProps {
  open: boolean;
  onClose: () => void;
  onSave: (data: Partial<Cotizacion>) => Promise<void>;
  cotizacion: Partial<Cotizacion> | null;
}

const CotizacionForm: React.FC<CotizacionFormProps> = ({ open, onClose, onSave, cotizacion }) => {
  const { handleSubmit, control, reset, watch, setValue, formState: { isSubmitting } } = useForm<Partial<Cotizacion>>({
    defaultValues: {
      items: []
    },
  });

  const { fields, append, remove } = useFieldArray({
    control,
    name: "items"
  });

  const watchedItems = watch("items");

  // State for details modal
  const [detailsModalOpen, setDetailsModalOpen] = useState(false);
  const [editingItemIndex, setEditingItemIndex] = useState<number | null>(null);

  useEffect(() => {
    if (open) {
      reset(cotizacion || { items: [] });
    }
  }, [open, cotizacion, reset]);

  const handleSave = async (data: Partial<Cotizacion>) => {
    try {
      await onSave(data);
      onClose();
    } catch (error) {
      console.error("Failed to save cotizacion:", error);
    }
  };

  const handleOpenDetails = (index: number) => {
    setEditingItemIndex(index);
    setDetailsModalOpen(true);
  };

  const handleCloseDetails = () => {
    setDetailsModalOpen(false);
    setEditingItemIndex(null);
  };

  const handleSaveDetails = (data: any) => {
    if (editingItemIndex !== null) {
      setValue(`items.${editingItemIndex}.detalles_json`, data, { shouldValidate: true });
    }
    handleCloseDetails();
  };

  return (
    <>
      <Dialog open={open} onClose={onClose} maxWidth="lg" fullWidth>
        <DialogTitle>{cotizacion?.id_cotizacion ? 'Editar' : 'Crear'} Cotización</DialogTitle>
        <form onSubmit={handleSubmit(handleSave)}>
          <DialogContent>
            <Grid container spacing={2} sx={{ mt: 1 }}>
              {/* Cotizacion Fields */}
              <Grid item xs={12} sm={6}><Controller name="cliente" control={control} render={({ field }) => <TextField {...field} label="ID Cliente" fullWidth />} /></Grid>
              <Grid item xs={12} sm={6}><Controller name="destino" control={control} render={({ field }) => <TextField {...field} label="Destino" fullWidth />} /></Grid>
              <Grid item xs={12} sm={6}><Controller name="terminos_pago" control={control} render={({ field }) => <TextField {...field} label="Términos de Pago" multiline rows={2} fullWidth />} /></Grid>
              <Grid item xs={12} sm={6}><Controller name="terminos_cancelacion" control={control} render={({ field }) => <TextField {...field} label="Términos de Cancelación" multiline rows={2} fullWidth />} /></Grid>

              {/* Items Section */}
              <Grid item xs={12}>
                <Typography variant="h6" sx={{ mt: 2 }}>Items de la Cotización</Typography>
                {fields.map((item, index) => {
                  const currentItem = watchedItems?.[index];
                  const hasDetails = currentItem?.tipo_item && ['VUE', 'ALO', 'ACT'].includes(currentItem.tipo_item);
                  return (
                    <Grid container spacing={1} key={item.id} alignItems="center" sx={{ mt: 1 }}>
                      <Grid item xs={2.5}><Controller name={`items.${index}.tipo_item`} control={control} defaultValue="OTR" render={({ field }) => (<FormControl fullWidth><InputLabel>Tipo</InputLabel><Select {...field} label="Tipo"><MenuItem value="VUE">Vuelo</MenuItem><MenuItem value="ALO">Alojamiento</MenuItem><MenuItem value="ACT">Actividad</MenuItem><MenuItem value="SEG">Seguro</MenuItem><MenuItem value="OTR">Otro</MenuItem></Select></FormControl>)} /></Grid>
                      <Grid item xs={4}><Controller name={`items.${index}.descripcion`} control={control} render={({ field }) => <TextField {...field} label="Descripción" fullWidth />} /></Grid>
                      <Grid item xs={2}><Controller name={`items.${index}.costo`} control={control} render={({ field }) => <TextField {...field} label="Costo" type="number" fullWidth />} /></Grid>
                      <Grid item xs={2.5} sx={{ textAlign: 'center' }}>
                        <Button startIcon={<EditIcon />} onClick={() => handleOpenDetails(index)} disabled={!hasDetails} size="small">
                          Detalles
                        </Button>
                      </Grid>
                      <Grid item xs={1}><IconButton onClick={() => remove(index)}><DeleteIcon /></IconButton></Grid>
                    </Grid>
                  );
                })}
                <Button variant="outlined" onClick={() => append({ tipo_item: 'OTR', descripcion: '', costo: '0.00' })} sx={{ mt: 2 }}>
                  Añadir Item
                </Button>
              </Grid>
            </Grid>
          </DialogContent>
          <DialogActions>
            <Button onClick={onClose} color="secondary">Cancelar</Button>
            <Button type="submit" variant="contained" disabled={isSubmitting}>{isSubmitting ? 'Guardando...' : 'Guardar'}</Button>
          </DialogActions>
        </form>
      </Dialog>

      {editingItemIndex !== null && watchedItems?.[editingItemIndex] && (
        <ItemDetallesForm
          open={detailsModalOpen}
          onClose={handleCloseDetails}
          onSave={handleSaveDetails}
          tipo={watchedItems[editingItemIndex].tipo_item as TipoItemCotizacion}
          initialData={watchedItems[editingItemIndex].detalles_json || {}}
        />
      )}
    </>
  );
};

export default CotizacionForm;
