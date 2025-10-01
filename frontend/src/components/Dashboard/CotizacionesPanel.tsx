'use client';

import React, { useState } from 'react';
import {
  Card,
  CardContent,
  Typography,
  Box,
  Button,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Grid,
  Alert
} from '@mui/material';
import { Email, Visibility, CheckCircle, Cancel } from '@mui/icons-material';
import { useApi } from '@/hooks/useApi';
import { apiMutate } from '@/lib/api';

interface Cotizacion {
  id_cotizacion: number;
  numero_cotizacion: string;
  cliente_nombre: string;
  destino: string;
  total_cotizado: number;
  estado: string;
  estado_display: string;
  fecha_emision: string;
  fecha_vencimiento: string;
  fecha_envio: string;
  fecha_vista: string;
  email_enviado: boolean;
}

const getEstadoColor = (estado: string) => {
  switch (estado) {
    case 'BOR': return 'default';
    case 'ENV': return 'info';
    case 'VIS': return 'primary';
    case 'ACE': return 'success';
    case 'REC': return 'error';
    case 'VEN': return 'warning';
    case 'CON': return 'success';
    default: return 'default';
  }
};

export default function CotizacionesPanel() {
  const { data: cotizaciones, isLoading, error, mutate } = useApi<{ results: Cotizacion[] }>('/api/cotizaciones/');
  const [selectedCotizacion, setSelectedCotizacion] = useState<Cotizacion | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  const handleAction = async (cotizacionId: number, action: string) => {
    setActionLoading(true);
    try {
      await apiMutate(`/api/cotizaciones/${cotizacionId}/${action}/`, { method: 'POST' });
      mutate(); // Recargar datos
      setSelectedCotizacion(null);
    } catch (error) {
      console.error(`Error en acción ${action}:`, error);
    } finally {
      setActionLoading(false);
    }
  };

  if (isLoading) return <Typography>Cargando cotizaciones...</Typography>;
  if (error) return <Alert severity="error">Error: {error.message}</Alert>;

  const cotizacionesList = cotizaciones?.results || [];

  return (
    <Box>
      <Typography variant="h6" gutterBottom color="text.primary">
        Cotizaciones Recientes
      </Typography>
      
      <Grid container spacing={2}>
        {cotizacionesList.slice(0, 6).map((cotizacion) => (
          <Grid item xs={12} md={6} key={cotizacion.id_cotizacion}>
            <Card>
              <CardContent>
                <Box display="flex" justifyContent="space-between" alignItems="start" mb={2}>
                  <Typography variant="h6">
                    {cotizacion.numero_cotizacion}
                  </Typography>
                  <Chip 
                    label={cotizacion.estado_display} 
                    color={getEstadoColor(cotizacion.estado)}
                    size="small"
                  />
                </Box>
                
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Cliente: {cotizacion.cliente_nombre}
                </Typography>
                
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Destino: {cotizacion.destino || 'No especificado'}
                </Typography>
                
                <Typography variant="h6" color="primary" gutterBottom>
                  ${cotizacion.total_cotizado.toLocaleString()}
                </Typography>
                
                <Box display="flex" gap={1} mt={2}>
                  {cotizacion.estado === 'BOR' && (
                    <Button
                      size="small"
                      startIcon={<Email />}
                      onClick={() => handleAction(cotizacion.id_cotizacion, 'marcar_enviada')}
                      disabled={actionLoading}
                    >
                      Enviar
                    </Button>
                  )}
                  
                  {cotizacion.estado === 'ENV' && (
                    <Button
                      size="small"
                      startIcon={<Visibility />}
                      onClick={() => handleAction(cotizacion.id_cotizacion, 'marcar_vista')}
                      disabled={actionLoading}
                    >
                      Marcar Vista
                    </Button>
                  )}
                  
                  {cotizacion.estado === 'ACE' && (
                    <Button
                      size="small"
                      startIcon={<CheckCircle />}
                      onClick={() => handleAction(cotizacion.id_cotizacion, 'convertir_a_venta')}
                      disabled={actionLoading}
                      variant="contained"
                    >
                      Convertir a Venta
                    </Button>
                  )}
                  
                  <Button
                    size="small"
                    onClick={() => setSelectedCotizacion(cotizacion)}
                  >
                    Ver Detalles
                  </Button>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Dialog de detalles */}
      <Dialog 
        open={!!selectedCotizacion} 
        onClose={() => setSelectedCotizacion(null)}
        maxWidth="sm"
        fullWidth
      >
        {selectedCotizacion && (
          <>
            <DialogTitle>
              Cotización {selectedCotizacion.numero_cotizacion}
            </DialogTitle>
            <DialogContent>
              <Box display="flex" flexDirection="column" gap={2}>
                <Typography><strong>Cliente:</strong> {selectedCotizacion.cliente_nombre}</Typography>
                <Typography><strong>Estado:</strong> {selectedCotizacion.estado_display}</Typography>
                <Typography><strong>Total:</strong> ${selectedCotizacion.total_cotizado.toLocaleString()}</Typography>
                <Typography><strong>Fecha Emisión:</strong> {new Date(selectedCotizacion.fecha_emision).toLocaleDateString()}</Typography>
                {selectedCotizacion.fecha_envio && (
                  <Typography><strong>Fecha Envío:</strong> {new Date(selectedCotizacion.fecha_envio).toLocaleDateString()}</Typography>
                )}
                {selectedCotizacion.fecha_vista && (
                  <Typography><strong>Fecha Vista:</strong> {new Date(selectedCotizacion.fecha_vista).toLocaleDateString()}</Typography>
                )}
              </Box>
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setSelectedCotizacion(null)}>
                Cerrar
              </Button>
            </DialogActions>
          </>
        )}
      </Dialog>
    </Box>
  );
}