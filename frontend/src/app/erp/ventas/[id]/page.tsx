'use client';

import React, { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import { 
  Box, Typography, Alert, CircularProgress, Paper, Grid, Chip,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow 
} from '@mui/material';

// --- Interfaces based on Django Models ---
interface VentaDetail {
  [key: string]: any; // Keep for flexibility
  items_venta: any[];
  segmentos_vuelo: any[];
  alojamientos: any[];
  actividades: any[];
  alquileres_autos: any[];
  pagos_venta: any[];
}

// --- Reusable Table Components ---

const ItemsVentaTable = ({ items }: { items: any[] }) => (
  <Paper sx={{ p: 2, mt: 2 }}>
    <Typography variant="h6" gutterBottom sx={{ pl: 2, pt: 1 }}>Items de Venta</Typography>
    <TableContainer>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Descripción</TableCell>
            <TableCell align="right">Cantidad</TableCell>
            <TableCell align="right">Precio Unitario</TableCell>
            <TableCell align="right">Total</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {items.map((item) => (
            <TableRow key={item.id_item_venta}>
              <TableCell>{item.descripcion_personalizada}</TableCell>
              <TableCell align="right">{item.cantidad}</TableCell>
              <TableCell align="right">{parseFloat(item.precio_unitario_venta).toFixed(2)}</TableCell>
              <TableCell align="right">{parseFloat(item.total_item_venta).toFixed(2)}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  </Paper>
);

const VuelosTable = ({ segmentos }: { segmentos: any[] }) => (
  <Paper sx={{ p: 2, mt: 2 }}>
    <Typography variant="h6" gutterBottom sx={{ pl: 2, pt: 1 }}>Vuelos</Typography>
    <TableContainer>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Origen</TableCell>
            <TableCell>Destino</TableCell>
            <TableCell>Aerolínea</TableCell>
            <TableCell>Vuelo</TableCell>
            <TableCell>Salida</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {segmentos.map((seg) => (
            <TableRow key={seg.id_segmento_vuelo}>
              <TableCell>{seg.origen_detalle?.nombre || seg.origen}</TableCell>
              <TableCell>{seg.destino_detalle?.nombre || seg.destino}</TableCell>
              <TableCell>{seg.aerolinea}</TableCell>
              <TableCell>{seg.numero_vuelo}</TableCell>
              <TableCell>{new Date(seg.fecha_salida).toLocaleString('es-VE')}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  </Paper>
);

const AlojamientosTable = ({ alojamientos }: { alojamientos: any[] }) => (
  <Paper sx={{ p: 2, mt: 2 }}>
    <Typography variant="h6" gutterBottom sx={{ pl: 2, pt: 1 }}>Alojamientos</Typography>
    <TableContainer>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Establecimiento</TableCell>
            <TableCell>Ciudad</TableCell>
            <TableCell>Check-in</TableCell>
            <TableCell>Check-out</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {alojamientos.map((h) => (
            <TableRow key={h.id_alojamiento_reserva}>
              <TableCell>{h.nombre_establecimiento}</TableCell>
              <TableCell>{h.ciudad_detalle?.nombre || h.ciudad}</TableCell>
              <TableCell>{new Date(h.check_in).toLocaleDateString('es-VE')}</TableCell>
              <TableCell>{new Date(h.check_out).toLocaleDateString('es-VE')}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  </Paper>
);

const ActividadesTable = ({ actividades }: { actividades: any[] }) => (
    <Paper sx={{ p: 2, mt: 2 }}>
        <Typography variant="h6" gutterBottom sx={{ pl: 2, pt: 1 }}>Actividades</Typography>
        <TableContainer>
        <Table size="small">
            <TableHead>
            <TableRow>
                <TableCell>Nombre</TableCell>
                <TableCell>Fecha</TableCell>
                <TableCell>Proveedor</TableCell>
                <TableCell align="right">Duración (hrs)</TableCell>
            </TableRow>
            </TableHead>
            <TableBody>
            {actividades.map((act) => (
                <TableRow key={act.id_actividad_servicio}>
                <TableCell>{act.nombre}</TableCell>
                <TableCell>{new Date(act.fecha).toLocaleDateString('es-VE')}</TableCell>
                <TableCell>{act.proveedor_detalle}</TableCell>
                <TableCell align="right">{act.duracion_horas}</TableCell>
                </TableRow>
            ))}
            </TableBody>
        </Table>
        </TableContainer>
    </Paper>
);

const PagosTable = ({ pagos }: { pagos: any[] }) => (
    <Paper sx={{ p: 2, mt: 2 }}>
      <Typography variant="h6" gutterBottom sx={{ pl: 2, pt: 1 }}>Historial de Pagos</Typography>
      <TableContainer>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Fecha</TableCell>
              <TableCell>Método</TableCell>
              <TableCell>Referencia</TableCell>
              <TableCell align="right">Monto</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {pagos.map((pago) => (
              <TableRow key={pago.id_pago_venta}>
                <TableCell>{new Date(pago.fecha_pago).toLocaleDateString('es-VE')}</TableCell>
                <TableCell>{pago.metodo_display}</TableCell>
                <TableCell>{pago.referencia}</TableCell>
                <TableCell align="right">{`${pago.moneda_detalle?.simbolo || '$'} ${parseFloat(pago.monto).toFixed(2)}`}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Paper>
  );

// --- Main Detail Page Component ---

export default function VentaDetailPage() {
  const params = useParams();
  const { id } = params;

  const [venta, setVenta] = useState<VentaDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const API_BASE = (process.env.NEXT_PUBLIC_API_BASE_URL || '').replace(/\/$/, '');

  useEffect(() => {
    if (!id) return;

    async function fetchVentaDetail() {
      try {
        setLoading(true);
        const url = API_BASE ? `${API_BASE}/api/ventas/${id}/` : `/api/ventas/${id}/`;
        const response = await fetch(url);
        if (!response.ok) {
          throw new Error(`Error ${response.status}: No se pudo encontrar la venta.`);
        }
        const data = await response.json();
        setVenta(data);
      } catch (e: any) {
        setError(`Error al cargar los detalles: ${e.message}`);
      } finally {
        setLoading(false);
      }
    }

    fetchVentaDetail();
  }, [id, API_BASE]);

  if (loading) {
    return <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}><CircularProgress /></Box>;
  }

  if (error) {
    return <Alert severity="error">{error}</Alert>;
  }

  if (!venta) {
    return <Alert severity="warning">No se encontraron datos para esta venta.</Alert>;
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'PAG': case 'CNF': return 'success';
      case 'PEN': case 'PAR': return 'warning';
      case 'CAN': return 'error';
      default: return 'default';
    }
  };

  const hasProducts = [venta.items_venta, venta.segmentos_vuelo, venta.alojamientos, venta.actividades, venta.alquileres_autos].some(arr => arr && arr.length > 0);

  return (
    <Box sx={{ p: 3, maxWidth: 1400, margin: 'auto' }}>
      <Typography variant="h4" gutterBottom>
        Detalle de Venta
      </Typography>
      
      {/* --- Main Info Header --- */}
      <Paper sx={{ p: 3, mt: 2, mb: 3 }}>
        <Grid container spacing={3}>
          <Grid item xs={12} sm={6} md={3}>
            <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1 }}>Localizador</Typography>
            <Typography variant="h6" component="p">{venta.localizador || 'N/A'}</Typography>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1 }}>Cliente</Typography>
            <Typography variant="h6" component="p">{venta.cliente_detalle?.get_nombre_completo || 'N/A'}</Typography>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1 }}>Fecha</Typography>
            <Typography variant="h6" component="p">{new Date(venta.fecha_venta).toLocaleDateString('es-VE')}</Typography>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1 }}>Estado</Typography>
            <Chip label={venta.estado_display} color={getStatusColor(venta.estado)} />
          </Grid>
        </Grid>
      </Paper>

      <Grid container spacing={3}>
        {/* --- Left Column: Products & Services --- */}
        <Grid item xs={12} md={8}>
            <Typography variant="h5" gutterBottom>Productos y Servicios</Typography>
            {venta.items_venta && venta.items_venta.length > 0 && <ItemsVentaTable items={venta.items_venta} />}
            {venta.segmentos_vuelo && venta.segmentos_vuelo.length > 0 && <VuelosTable segmentos={venta.segmentos_vuelo} />}
            {venta.alojamientos && venta.alojamientos.length > 0 && <AlojamientosTable alojamientos={venta.alojamientos} />}
            {venta.actividades && venta.actividades.length > 0 && <ActividadesTable actividades={venta.actividades} />}
            {!hasProducts && <Alert severity="info">No hay productos o servicios detallados para esta venta.</Alert>}
        </Grid>

        {/* --- Right Column: Financials & Payments --- */}
        <Grid item xs={12} md={4}>
            <Typography variant="h5" gutterBottom>Finanzas</Typography>
            <Paper sx={{ p: 2, mt: 2 }}>
                <Grid container spacing={1.5}>
                    <Grid item xs={6}><Typography variant="body1">Subtotal:</Typography></Grid>
                    <Grid item xs={6}><Typography variant="body1" align="right">{parseFloat(venta.subtotal).toFixed(2)}</Typography></Grid>
                    <Grid item xs={6}><Typography variant="body1">Impuestos:</Typography></Grid>
                    <Grid item xs={6}><Typography variant="body1" align="right">{parseFloat(venta.impuestos).toFixed(2)}</Typography></Grid>
                    <Grid item xs={12}><hr/></Grid>
                    <Grid item xs={6}><Typography variant="h6">Total:</Typography></Grid>
                    <Grid item xs={6}><Typography variant="h6" align="right">{parseFloat(venta.total_venta).toFixed(2)}</Typography></Grid>
                    <Grid item xs={6}><Typography variant="body1" color="success.main">Pagado:</Typography></Grid>
                    <Grid item xs={6}><Typography variant="body1" align="right" color="success.main">{parseFloat(venta.monto_pagado).toFixed(2)}</Typography></Grid>
                    <Grid item xs={6}><Typography variant="h6" color="error.main">Saldo:</Typography></Grid>
                    <Grid item xs={6}><Typography variant="h6" align="right" color="error.main">{parseFloat(venta.saldo_pendiente).toFixed(2)}</Typography></Grid>
                </Grid>
            </Paper>

            {venta.pagos_venta && venta.pagos_venta.length > 0 && <PagosTable pagos={venta.pagos_venta} />}
        </Grid>
      </Grid>

    </Box>
  );
}