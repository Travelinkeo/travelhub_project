'use client';

import { useParams } from 'next/navigation';
import { Box, Typography, Button, Card, CardContent, Chip, Alert, CircularProgress } from '@mui/material';
import { useApi } from '@/hooks/useApi';
import { Venta } from '@/types/api';

export default function VentaDetallePage() {
  const params = useParams();
  const id = params.id as string;
  
  const { data: venta, isLoading, error } = useApi<Venta>(`/api/ventas/${id}/`);

  const handleGenerarVoucher = async (servicioId: number) => {
    try {
      const token = localStorage.getItem('auth_token') || localStorage.getItem('access_token');
      const response = await fetch(`http://localhost:8000/api/servicios-adicionales/${servicioId}/generar_voucher/`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      
      if (!response.ok) throw new Error('Error al generar voucher');
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Voucher-Servicio-${servicioId}.pdf`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      alert('Error al generar voucher: ' + (e instanceof Error ? e.message : 'Error desconocido'));
    }
  };

  const handleGenerarVoucherAlojamiento = async (alojamientoId: number) => {
    try {
      const token = localStorage.getItem('auth_token') || localStorage.getItem('access_token');
      const response = await fetch(`http://localhost:8000/api/alojamientos/${alojamientoId}/generar_voucher/`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      
      if (!response.ok) throw new Error('Error al generar voucher');
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Voucher-Alojamiento-${alojamientoId}.pdf`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      alert('Error al generar voucher: ' + (e instanceof Error ? e.message : 'Error desconocido'));
    }
  };

  const handleGenerarVoucherGenerico = async (tipo: string, id: number, endpoint: string) => {
    try {
      const token = localStorage.getItem('auth_token') || localStorage.getItem('access_token');
      const response = await fetch(`http://localhost:8000${endpoint}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Error al generar voucher');
      }
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Voucher-${tipo}-${id}.pdf`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      alert('Error: ' + (e instanceof Error ? e.message : 'Error desconocido'));
    }
  };

  if (isLoading) return <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}><CircularProgress /></Box>;
  if (error) return <Alert severity="error">Error al cargar la venta: {error.message}</Alert>;
  if (!venta) return <Alert severity="warning">Venta no encontrada</Alert>;

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        Venta {venta.localizador}
      </Typography>

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>Información General</Typography>
          <Typography>Cliente: {venta.cliente_detalle?.get_nombre_completo}</Typography>
          <Typography>Fecha: {new Date(venta.fecha_venta).toLocaleDateString()}</Typography>
          <Typography>Total: {venta.moneda_detalle?.codigo_iso} {parseFloat(venta.total_venta).toFixed(2)}</Typography>
          <Chip label={venta.estado} color="primary" size="small" sx={{ mt: 1 }} />
        </CardContent>
      </Card>

      {venta.alojamientos && venta.alojamientos.length > 0 && (
        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" gutterBottom>Alojamientos</Typography>
          {venta.alojamientos.map((alojamiento: any) => (
            <Card key={alojamiento.id_alojamiento_reserva} sx={{ mb: 2 }}>
              <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Box>
                    <Typography variant="subtitle1" fontWeight="bold">
                      {alojamiento.nombre_establecimiento}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Ciudad: {alojamiento.ciudad_detalle?.nombre || 'N/A'}
                    </Typography>
                    {alojamiento.check_in && alojamiento.check_out && (
                      <Typography variant="body2">
                        {new Date(alojamiento.check_in).toLocaleDateString()} - {new Date(alojamiento.check_out).toLocaleDateString()}
                      </Typography>
                    )}
                    {alojamiento.habitaciones && (
                      <Typography variant="body2">
                        Habitaciones: {alojamiento.habitaciones}
                      </Typography>
                    )}
                  </Box>
                  <Button
                    variant="contained"
                    color="primary"
                    onClick={() => handleGenerarVoucherAlojamiento(alojamiento.id_alojamiento_reserva)}
                  >
                    Generar Voucher
                  </Button>
                </Box>
              </CardContent>
            </Card>
          ))}
        </Box>
      )}

      {venta.servicios_adicionales && venta.servicios_adicionales.length > 0 && (
        <Box>
          <Typography variant="h6" gutterBottom>Servicios Adicionales</Typography>
          {venta.servicios_adicionales.map((servicio) => (
            <Card key={servicio.id_servicio_adicional} sx={{ mb: 2 }}>
              <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Box>
                    <Typography variant="subtitle1" fontWeight="bold">
                      {servicio.descripcion}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Código: {servicio.codigo_referencia || 'N/A'}
                    </Typography>
                    {servicio.fecha_inicio && (
                      <Typography variant="body2">
                        Fecha: {new Date(servicio.fecha_inicio).toLocaleDateString()}
                      </Typography>
                    )}
                  </Box>
                  <Button
                    variant="contained"
                    color="primary"
                    onClick={() => handleGenerarVoucher(servicio.id_servicio_adicional)}
                  >
                    Generar Voucher
                  </Button>
                </Box>
              </CardContent>
            </Card>
          ))}
        </Box>
      )}

      {venta.alquileres_autos && venta.alquileres_autos.length > 0 && (
        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" gutterBottom>Alquileres de Auto</Typography>
          {venta.alquileres_autos.map((alquiler: any) => (
            <Card key={alquiler.id_alquiler_auto} sx={{ mb: 2 }}>
              <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Box>
                    <Typography variant="subtitle1" fontWeight="bold">
                      {alquiler.compania_rentadora} - {alquiler.categoria_auto}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Confirmación: {alquiler.numero_confirmacion || 'N/A'}
                    </Typography>
                    {alquiler.fecha_hora_retiro && alquiler.fecha_hora_devolucion && (
                      <Typography variant="body2">
                        {new Date(alquiler.fecha_hora_retiro).toLocaleDateString()} - {new Date(alquiler.fecha_hora_devolucion).toLocaleDateString()}
                      </Typography>
                    )}
                  </Box>
                  <Button
                    variant="contained"
                    color="primary"
                    onClick={() => handleGenerarVoucherGenerico('AlquilerAuto', alquiler.id_alquiler_auto, `/api/alquileres-autos/${alquiler.id_alquiler_auto}/generar_voucher/`)}
                  >
                    Generar Voucher
                  </Button>
                </Box>
              </CardContent>
            </Card>
          ))}
        </Box>
      )}

      {venta.traslados && venta.traslados.length > 0 && (
        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" gutterBottom>Traslados</Typography>
          {venta.traslados.map((traslado: any) => (
            <Card key={traslado.id_traslado_servicio} sx={{ mb: 2 }}>
              <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Box>
                    <Typography variant="subtitle1" fontWeight="bold">
                      {traslado.tipo_traslado_display}: {traslado.origen} → {traslado.destino}
                    </Typography>
                    {traslado.fecha_hora && (
                      <Typography variant="body2">
                        {new Date(traslado.fecha_hora).toLocaleString()}
                      </Typography>
                    )}
                    <Typography variant="body2" color="text.secondary">
                      Pasajeros: {traslado.pasajeros}
                    </Typography>
                  </Box>
                  <Button
                    variant="contained"
                    color="primary"
                    onClick={() => handleGenerarVoucherGenerico('Traslado', traslado.id_traslado_servicio, `/api/traslados/${traslado.id_traslado_servicio}/generar_voucher/`)}
                  >
                    Generar Voucher
                  </Button>
                </Box>
              </CardContent>
            </Card>
          ))}
        </Box>
      )}

      {venta.actividades && venta.actividades.length > 0 && (
        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" gutterBottom>Actividades y Excursiones</Typography>
          {venta.actividades.map((actividad: any) => (
            <Card key={actividad.id_actividad_servicio} sx={{ mb: 2 }}>
              <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Box>
                    <Typography variant="subtitle1" fontWeight="bold">
                      {actividad.nombre}
                    </Typography>
                    {actividad.fecha && (
                      <Typography variant="body2">
                        {new Date(actividad.fecha).toLocaleDateString()}
                      </Typography>
                    )}
                    {actividad.duracion_horas && (
                      <Typography variant="body2" color="text.secondary">
                        Duración: {actividad.duracion_horas} horas
                      </Typography>
                    )}
                  </Box>
                  <Button
                    variant="contained"
                    color="primary"
                    onClick={() => handleGenerarVoucherGenerico('Actividad', actividad.id_actividad_servicio, `/api/actividades/${actividad.id_actividad_servicio}/generar_voucher/`)}
                  >
                    Generar Voucher
                  </Button>
                </Box>
              </CardContent>
            </Card>
          ))}
        </Box>
      )}

      {(!venta.alojamientos || venta.alojamientos.length === 0) && 
       (!venta.servicios_adicionales || venta.servicios_adicionales.length === 0) &&
       (!venta.alquileres_autos || venta.alquileres_autos.length === 0) &&
       (!venta.traslados || venta.traslados.length === 0) &&
       (!venta.actividades || venta.actividades.length === 0) && (
        <Alert severity="info">Esta venta no tiene servicios asociados</Alert>
      )}
    </Box>
  );
}
