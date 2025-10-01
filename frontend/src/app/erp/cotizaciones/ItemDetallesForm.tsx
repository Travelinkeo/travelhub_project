'use client';

import React, { useEffect } from 'react';
import { useForm, Controller } from 'react-hook-form';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
  Grid,
  Box,
  Typography
} from '@mui/material';
import { TipoItemCotizacion } from '@/types/api';

interface ItemDetallesFormProps {
  open: boolean;
  onClose: () => void;
  onSave: (data: any) => void;
  tipo: TipoItemCotizacion;
  initialData: any;
}

const VueloFields: React.FC<{ control: any }> = ({ control }) => (
  <Grid container spacing={2} sx={{ mt: 1 }}>
    <Grid item xs={12}><Controller name="ruta" control={control} render={({ field }) => <TextField {...field} label="Ruta (ej. CCS-MAD)" fullWidth />} /></Grid>
    <Grid item xs={12}><Controller name="aerolinea" control={control} render={({ field }) => <TextField {...field} label="Aerolínea" fullWidth />} /></Grid>
    <Grid item xs={6}><Controller name="fecha_salida" control={control} render={({ field }) => <TextField {...field} label="Fecha Salida" type="date" InputLabelProps={{ shrink: true }} fullWidth />} /></Grid>
    <Grid item xs={6}><Controller name="fecha_regreso" control={control} render={({ field }) => <TextField {...field} label="Fecha Regreso" type="date" InputLabelProps={{ shrink: true }} fullWidth />} /></Grid>
    <Grid item xs={12}><Controller name="incluye" control={control} render={({ field }) => <TextField {...field} label="Incluye" fullWidth />} /></Grid>
  </Grid>
);

const AlojamientoFields: React.FC<{ control: any }> = ({ control }) => (
  <Grid container spacing={2} sx={{ mt: 1 }}>
    <Grid item xs={12}><Controller name="hotel" control={control} render={({ field }) => <TextField {...field} label="Nombre del Hotel" fullWidth />} /></Grid>
    <Grid item xs={6}><Controller name="check_in" control={control} render={({ field }) => <TextField {...field} label="Fecha Check-in" type="date" InputLabelProps={{ shrink: true }} fullWidth />} /></Grid>
    <Grid item xs={6}><Controller name="check_out" control={control} render={({ field }) => <TextField {...field} label="Fecha Check-out" type="date" InputLabelProps={{ shrink: true }} fullWidth />} /></Grid>
    <Grid item xs={6}><Controller name="noches" control={control} render={({ field }) => <TextField {...field} label="Noches" type="number" fullWidth />} /></Grid>
    <Grid item xs={6}><Controller name="regimen" control={control} render={({ field }) => <TextField {...field} label="Régimen (ej. Desayuno incluido)" fullWidth />} /></Grid>
  </Grid>
);

const ActividadFields: React.FC<{ control: any }> = ({ control }) => (
  <Grid container spacing={2} sx={{ mt: 1 }}>
    <Grid item xs={12}><Controller name="actividad" control={control} render={({ field }) => <TextField {...field} label="Nombre de la Actividad" fullWidth />} /></Grid>
    <Grid item xs={6}><Controller name="fecha" control={control} render={({ field }) => <TextField {...field} label="Fecha" type="date" InputLabelProps={{ shrink: true }} fullWidth />} /></Grid>
    <Grid item xs={6}><Controller name="incluye" control={control} render={({ field }) => <TextField {...field} label="Incluye" fullWidth />} /></Grid>
  </Grid>
);

const ItemDetallesForm: React.FC<ItemDetallesFormProps> = ({ open, onClose, onSave, tipo, initialData }) => {
  const { handleSubmit, control, reset } = useForm({ defaultValues: initialData || {} });

  useEffect(() => {
    reset(initialData || {});
  }, [initialData, reset]);

  const renderFields = () => {
    switch (tipo) {
      case 'VUE': return <VueloFields control={control} />;
      case 'ALO': return <AlojamientoFields control={control} />;
      case 'ACT': return <ActividadFields control={control} />;
      default: return <Typography sx={{ mt: 2 }}>No hay detalles adicionales para este tipo de item.</Typography>;
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Detalles del Item</DialogTitle>
      <form onSubmit={handleSubmit(onSave)}>
        <DialogContent>
          {renderFields()}
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose}>Cancelar</Button>
          <Button type="submit" variant="contained">Guardar Detalles</Button>
        </DialogActions>
      </form>
    </Dialog>
  );
};

export default ItemDetallesForm;
