'use client';

import React from 'react';
import { Card, CardContent, Typography, Grid, Box, Chip } from '@mui/material';
import { TrendingUp, AttachMoney, Schedule, ShoppingCart } from '@mui/icons-material';
import { useApi } from '@/hooks/useApi';

interface DashboardStatsData {
  ventas_mes: { total: number; count: number };
  ventas_30d: { total: number; count: number };
  pendientes_pago: { total: number; count: number };
  pagos_mes: { total: number };
  top_productos: Array<{
    producto_servicio__nombre: string;
    producto_servicio__tipo_producto: string;
    cantidad_total: number;
    monto_total: number;
  }>;
}

const StatCard = ({ title, value, subtitle, icon, color = 'primary' }: {
  title: string;
  value: string;
  subtitle: string;
  icon: React.ReactNode;
  color?: 'primary' | 'success' | 'warning' | 'info';
}) => (
  <Card sx={{ height: '100%' }}>
    <CardContent>
      <Box display="flex" alignItems="center" justifyContent="space-between">
        <Box>
          <Typography variant="h4" color={`${color}.main`} fontWeight="bold">
            {value}
          </Typography>
          <Typography variant="h6" color="text.primary">
            {title}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {subtitle}
          </Typography>
        </Box>
        <Box color={`${color}.main`}>
          {icon}
        </Box>
      </Box>
    </CardContent>
  </Card>
);

export default function DashboardStats() {
  const { data, isLoading, error } = useApi<DashboardStatsData>('/api/dashboard/stats/');

  if (isLoading) {
    return (
      <Box p={3}>
        <Typography>Cargando estadísticas...</Typography>
      </Box>
    );
  }

  if (error) {
    return (
      <Box p={3}>
        <Typography color="error">Error cargando estadísticas: {error.message}</Typography>
      </Box>
    );
  }

  if (!data) return null;

  return (
    <Box p={{ xs: 2, sm: 3 }}>
      <Typography variant="h4" gutterBottom sx={{ fontSize: { xs: '1.5rem', sm: '2rem' } }} color="text.primary">
        Resumen Ejecutivo
      </Typography>
      
      {/* KPI Cards */}
      <Grid container spacing={2} mb={4}>
        <Grid item xs={12} sm={6} lg={3}>
          <StatCard
            title="Ventas Este Mes"
            value={`$${data.ventas_mes.total.toLocaleString()}`}
            subtitle={`${data.ventas_mes.count} ventas`}
            icon={<TrendingUp fontSize="large" />}
            color="primary"
          />
        </Grid>
        <Grid item xs={12} sm={6} lg={3}>
          <StatCard
            title="Pagos Recibidos"
            value={`$${data.pagos_mes.total.toLocaleString()}`}
            subtitle="Este mes"
            icon={<AttachMoney fontSize="large" />}
            color="success"
          />
        </Grid>
        <Grid item xs={12} sm={6} lg={3}>
          <StatCard
            title="Pendiente de Pago"
            value={`$${data.pendientes_pago.total.toLocaleString()}`}
            subtitle={`${data.pendientes_pago.count} ventas`}
            icon={<Schedule fontSize="large" />}
            color="warning"
          />
        </Grid>
        <Grid item xs={12} sm={6} lg={3}>
          <StatCard
            title="Ventas Últimos 30d"
            value={data.ventas_30d.count.toString()}
            subtitle={`$${data.ventas_30d.total.toLocaleString()}`}
            icon={<ShoppingCart fontSize="large" />}
            color="info"
          />
        </Grid>
      </Grid>

      {/* Top Productos */}
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom color="text.primary">
            Top Productos (30 días)
          </Typography>
          {data.top_productos.length > 0 ? (
            data.top_productos.map((producto, index) => (
              <Box
                key={index}
                display="flex"
                justifyContent="space-between"
                alignItems="center"
                py={1}
                borderBottom={index < data.top_productos.length - 1 ? 1 : 0}
                borderColor="divider"
              >
                <Box>
                  <Typography variant="subtitle1" fontWeight="bold">
                    {producto.producto_servicio__nombre}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {producto.producto_servicio__tipo_producto}
                  </Typography>
                </Box>
                <Box textAlign="right">
                  <Chip 
                    label={`${producto.cantidad_total} unidades`} 
                    color="primary" 
                    size="small" 
                  />
                  <Typography variant="body2" color="text.secondary">
                    ${producto.monto_total.toLocaleString()}
                  </Typography>
                </Box>
              </Box>
            ))
          ) : (
            <Typography color="text.secondary">
              No hay datos de productos en los últimos 30 días
            </Typography>
          )}
        </CardContent>
      </Card>
    </Box>
  );
}