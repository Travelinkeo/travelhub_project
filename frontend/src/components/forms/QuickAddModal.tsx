'use client';

import React, { useState } from 'react';
import { Dialog, DialogTitle, DialogContent, DialogActions, Button, TextField, Grid, MenuItem } from '@mui/material';
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { apiMutate } from '@/lib/api';

const clienteSchema = z.object({
  nombres: z.string().min(1, 'Nombres requeridos'),
  apellidos: z.string().min(1, 'Apellidos requeridos'),
  email: z.string().email('Email inválido').optional().or(z.literal('')),
  telefono: z.string().optional(),
  nombre_empresa: z.string().optional(),
});

const proveedorSchema = z.object({
  nombre: z.string().min(1, 'Nombre requerido'),
  tipo_proveedor: z.string().min(1, 'Tipo requerido'),
  nivel_proveedor: z.string().min(1, 'Nivel requerido'),
  contacto_email: z.string().email('Email inválido').optional().or(z.literal('')),
  contacto_telefono: z.string().optional(),
  direccion: z.string().optional(),
});

const ciudadSchema = z.object({
  nombre: z.string().min(1, 'Nombre requerido'),
  pais: z.number().min(1, 'País requerido'),
  region_estado: z.string().optional(),
});

interface QuickAddModalProps {
  open: boolean;
  onClose: () => void;
  type: 'cliente' | 'proveedor' | 'ciudad';
  onSuccess: (newItem: any) => void;
}

export default function QuickAddModal({ open, onClose, type, onSuccess }: QuickAddModalProps) {
  const [isLoading, setIsLoading] = useState(false);

  const getSchema = () => {
    switch (type) {
      case 'cliente': return clienteSchema;
      case 'proveedor': return proveedorSchema;
      case 'ciudad': return ciudadSchema;
      default: return clienteSchema;
    }
  };

  const { control, handleSubmit, reset, formState: { errors } } = useForm({
    resolver: zodResolver(getSchema()),
  });

  const handleClose = () => {
    reset();
    onClose();
  };

  const onSubmit = async (data: any) => {
    setIsLoading(true);
    try {
      const endpoint = `/api/${type === 'cliente' ? 'clientes' : type === 'proveedor' ? 'proveedores' : 'ciudades'}/`;
      const result = await apiMutate(endpoint, { method: 'POST', body: data });
      onSuccess(result);
      handleClose();
    } catch (error) {
      alert(`Error al crear ${type}: ${error instanceof Error ? error.message : 'Error desconocido'}`);
    } finally {
      setIsLoading(false);
    }
  };

  const renderFields = () => {
    switch (type) {
      case 'cliente':
        return (
          <>
            <Grid item xs={6}>
              <Controller
                name="nombres"
                control={control}
                render={({ field }) => (
                  <TextField {...field} label="Nombres" fullWidth error={!!errors.nombres} helperText={errors.nombres?.message} />
                )}
              />
            </Grid>
            <Grid item xs={6}>
              <Controller
                name="apellidos"
                control={control}
                render={({ field }) => (
                  <TextField {...field} label="Apellidos" fullWidth error={!!errors.apellidos} helperText={errors.apellidos?.message} />
                )}
              />
            </Grid>
            <Grid item xs={6}>
              <Controller
                name="email"
                control={control}
                render={({ field }) => (
                  <TextField {...field} label="Email" type="email" fullWidth error={!!errors.email} helperText={errors.email?.message} />
                )}
              />
            </Grid>
            <Grid item xs={6}>
              <Controller
                name="telefono"
                control={control}
                render={({ field }) => <TextField {...field} label="Teléfono" fullWidth />}
              />
            </Grid>
            <Grid item xs={12}>
              <Controller
                name="nombre_empresa"
                control={control}
                render={({ field }) => <TextField {...field} label="Empresa (opcional)" fullWidth />}
              />
            </Grid>
          </>
        );

      case 'proveedor':
        return (
          <>
            <Grid item xs={12}>
              <Controller
                name="nombre"
                control={control}
                render={({ field }) => (
                  <TextField {...field} label="Nombre" fullWidth error={!!errors.nombre} helperText={errors.nombre?.message} />
                )}
              />
            </Grid>
            <Grid item xs={6}>
              <Controller
                name="tipo_proveedor"
                control={control}
                render={({ field }) => (
                  <TextField
                    {...field}
                    select
                    label="Tipo"
                    fullWidth
                    error={!!errors.tipo_proveedor}
                    helperText={errors.tipo_proveedor?.message}
                  >
                    <MenuItem value="CON">Consolidador</MenuItem>
                    <MenuItem value="MAY">Mayorista</MenuItem>
                    <MenuItem value="OTR">Otro</MenuItem>
                  </TextField>
                )}
              />
            </Grid>
            <Grid item xs={6}>
              <Controller
                name="nivel_proveedor"
                control={control}
                render={({ field }) => (
                  <TextField
                    {...field}
                    select
                    label="Nivel"
                    fullWidth
                    error={!!errors.nivel_proveedor}
                    helperText={errors.nivel_proveedor?.message}
                  >
                    <MenuItem value="CON">Consolidador</MenuItem>
                    <MenuItem value="MAY">Mayorista</MenuItem>
                    <MenuItem value="DIR">Directo</MenuItem>
                  </TextField>
                )}
              />
            </Grid>
            <Grid item xs={6}>
              <Controller
                name="contacto_email"
                control={control}
                render={({ field }) => <TextField {...field} label="Email Contacto" type="email" fullWidth />}
              />
            </Grid>
            <Grid item xs={6}>
              <Controller
                name="contacto_telefono"
                control={control}
                render={({ field }) => <TextField {...field} label="Teléfono Contacto" fullWidth />}
              />
            </Grid>
            <Grid item xs={12}>
              <Controller
                name="direccion"
                control={control}
                render={({ field }) => <TextField {...field} label="Dirección" fullWidth />}
              />
            </Grid>
          </>
        );

      case 'ciudad':
        return (
          <>
            <Grid item xs={12}>
              <Controller
                name="nombre"
                control={control}
                render={({ field }) => (
                  <TextField {...field} label="Nombre" fullWidth error={!!errors.nombre} helperText={errors.nombre?.message} />
                )}
              />
            </Grid>
            <Grid item xs={6}>
              <Controller
                name="pais"
                control={control}
                render={({ field }) => (
                  <TextField {...field} type="number" label="ID País" fullWidth error={!!errors.pais} helperText={errors.pais?.message} />
                )}
              />
            </Grid>
            <Grid item xs={6}>
              <Controller
                name="region_estado"
                control={control}
                render={({ field }) => <TextField {...field} label="Región/Estado" fullWidth />}
              />
            </Grid>
          </>
        );
    }
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle>Añadir {type === 'cliente' ? 'Cliente' : type === 'proveedor' ? 'Proveedor' : 'Ciudad'}</DialogTitle>
      <form onSubmit={handleSubmit(onSubmit)}>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            {renderFields()}
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleClose}>Cancelar</Button>
          <Button type="submit" variant="contained" disabled={isLoading}>
            {isLoading ? 'Guardando...' : 'Guardar'}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
}