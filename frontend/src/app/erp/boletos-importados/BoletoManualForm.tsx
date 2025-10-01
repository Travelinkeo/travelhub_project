
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
} from '@mui/material';
import { BoletoImportado } from '@/types/api';

interface BoletoManualFormProps {
  open: boolean;
  onClose: () => void;
  onSave: (data: Partial<BoletoImportado>) => Promise<void>;
  boleto: Partial<BoletoImportado> | null;
}

const BoletoManualForm: React.FC<BoletoManualFormProps> = ({ open, onClose, onSave, boleto }) => {
  const { handleSubmit, control, reset, formState: { isSubmitting } } = useForm<Partial<BoletoImportado>>({
    defaultValues: {},
  });

  useEffect(() => {
    if (open) {
      // Reset form with boleto data if editing, or empty if creating
      reset(boleto || {});
    }
  }, [open, boleto, reset]);

  const handleSave = async (data: Partial<BoletoImportado>) => {
    try {
      await onSave(data);
    } catch (error) {
      console.error("Failed to save boleto:", error);
      // Error is handled in the parent component's onSave function
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>{boleto ? 'Editar' : 'Ingresar'} Boleto Manualmente</DialogTitle>
      <form onSubmit={handleSubmit(handleSave)}>
        <DialogContent>
          <Box sx={{ mt: 2 }}>
            <Grid container spacing={2}>
              {/* Fila 1 */}
              <Grid item xs={12} sm={4}>
                <Controller
                  name="numero_boleto"
                  control={control}
                  render={({ field }) => <TextField {...field} label="Número de Boleto" fullWidth />}
                />
              </Grid>
              <Grid item xs={12} sm={4}>
                <Controller
                  name="nombre_pasajero_completo"
                  control={control}
                  render={({ field }) => <TextField {...field} label="Nombre Completo Pasajero (Original)" fullWidth />}
                />
              </Grid>
              <Grid item xs={12} sm={4}>
                <Controller
                  name="foid_pasajero"
                  control={control}
                  render={({ field }) => <TextField {...field} label="FOID/D.Identidad Pasajero" fullWidth />}
                />
              </Grid>

              {/* Fila 2 */}
              <Grid item xs={12} sm={4}>
                <Controller
                  name="localizador_pnr"
                  control={control}
                  render={({ field }) => <TextField {...field} label="Localizador (PNR)" fullWidth />}
                />
              </Grid>
              <Grid item xs={12} sm={4}>
                <Controller
                  name="agente_emisor"
                  control={control}
                  render={({ field }) => <TextField {...field} label="Agente Emisor" fullWidth />}
                />
              </Grid>
              <Grid item xs={12} sm={4}>
                <Controller
                  name="fecha_emision_boleto"
                  control={control}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      label="Fecha de Emisión del Boleto"
                      type="date"
                      InputLabelProps={{ shrink: true }}
                      fullWidth
                    />
                  )}
                />
              </Grid>

              {/* Fila 3 */}
              <Grid item xs={12} sm={6}>
                <Controller
                  name="aerolinea_emisora"
                  control={control}
                  render={({ field }) => <TextField {...field} label="Aerolínea Emisora" fullWidth />}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <Controller
                  name="direccion_aerolinea"
                  control={control}
                  render={({ field }) => <TextField {...field} label="Dirección Aerolínea" fullWidth />}
                />
              </Grid>

              {/* Fila 4 */}
              <Grid item xs={12}>
                <Controller
                  name="ruta_vuelo"
                  control={control}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      label="Ruta del Vuelo (Itinerario)"
                      multiline
                      rows={3}
                      fullWidth
                    />
                  )}
                />
              </Grid>

              {/* Fila 5 */}
              <Grid item xs={12} sm={4}>
                <Controller
                  name="tarifa_base"
                  control={control}
                  render={({ field }) => <TextField {...field} label="Tarifa Base" type="number" fullWidth />}
                />
              </Grid>
              <Grid item xs={12} sm={4}>
                <Controller
                  name="impuestos_descripcion"
                  control={control}
                  render={({ field }) => <TextField {...field} label="Descripción Impuestos" fullWidth />}
                />
              </Grid>
              <Grid item xs={12} sm={4}>
                <Controller
                  name="total_boleto"
                  control={control}
                  render={({ field }) => <TextField {...field} label="Total del Boleto" type="number" fullWidth />}
                />
              </Grid>
            </Grid>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose} color="secondary">
            Cancelar
          </Button>
          <Button type="submit" variant="contained" disabled={isSubmitting}>
            {isSubmitting ? 'Guardando...' : 'Guardar'}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
};

export default BoletoManualForm;
