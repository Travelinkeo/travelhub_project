'use client';

import React from 'react';
import { Card, CardContent, Typography, Grid, Box, Chip, Alert } from '@mui/material';
import { TrendingUp, AttachMoney, Schedule, ShoppingCart, ShowChart, CalendarToday } from '@mui/icons-material';
import { useApi } from '@/hooks/useApi';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface DashboardStatsData {
  ventas_mes: { total: number; count: number };
  ventas_ano: { total: number; count: number };
  ventas_30d: { total: number; count: number };
  pendientes_pago: { total: number; count: number };
  pagos_mes: { total: number };
  margen_promedio: number;
  top_productos: Array<{
    producto_servicio__nombre: string;
    producto_servicio__tipo_producto: string;
    cantidad_total: number;
    monto_total: number;
  }>;
  tendencia_7dias: Array<{
    fecha: string;
    total: number;
    count: number;
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
        <Typography variant="h6" gutterBottom>Estadísticas no disponibles</Typography>
        <Typography color="text.secondary">Las estadísticas del dashboard están temporalmente deshabilitadas.</Typography>
      </Box>
    );
  }

  if (!data) return null;

  return (
    <Box p={{ xs: 2, sm: 3 }}>
      <Typography variant="h4" gutterBottom sx={{ fontSize: { xs: '1.5rem', sm: '2rem' } }} color="text.primary">
        Resumen Ejecutivo
      </Typography>
      
      {/* Alertas */}
      {data.pendientes_pago.count > 0 && (
        <Alert severity="warning" sx={{ mb: 3 }}>
          Tienes {data.pendientes_pago.count} ventas pendientes de pago por ${data.pendientes_pago.total.toLocaleString()}
        </Alert>
      )}

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
            title="Ventas del Año"
            value={`$${data.ventas_ano.total.toLocaleString()}`}
            subtitle={`${data.ventas_ano.count} ventas`}
            icon={<CalendarToday fontSize="large" />}
            color="info"
          />
        </Grid>
      </Grid>

      {/* Gráfico de Tendencia */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom color="text.primary">
            <ShowChart sx={{ verticalAlign: 'middle', mr: 1 }} />
            Tendencia de Ventas (Últimos 7 días)
          </Typography>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={data.tendencia_7dias}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis 
                dataKey="fecha" 
                tickFormatter={(value) => new Date(value).toLocaleDateString('es', { month: 'short', day: 'numeric' })}
              />
              <YAxis />
              <Tooltip 
                formatter={(value: number) => `$${value.toLocaleString()}`}
                labelFormatter={(label) => new Date(label).toLocaleDateString('es', { weekday: 'long', month: 'long', day: 'numeric' })}
              />
              <Line type="monotone" dataKey="total" stroke="#1976d2" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Top Productos */}
      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom color="text.primary">
                Top Productos por Ingresos (30 días)
              </Typography>
              {data.top_productos.length > 0 ? (
                data.top_productos.map((producto, index) => (
                  <Box
                    key={index}
                    display="flex"
                    justifyContent="space-between"
                    alignItems="center"
                    py={1.5}
                    borderBottom={index < data.top_productos.length - 1 ? 1 : 0}
                    borderColor="divider"
                  >
                    <Box>
                      <Typography variant="subtitle1" fontWeight="bold">
                        {producto.producto_servicio__nombre}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        {producto.cantidad_total} unidades vendidas
                      </Typography>
                    </Box>
                    <Box textAlign="right">
                      <Typography variant="h6" color="primary.main">
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
        </Grid>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom color="text.primary">
                Resumen Rápido
              </Typography>
              <Box py={2}>
                <Typography variant="body2" color="text.secondary">Margen Promedio</Typography>
                <Typography variant="h5" color="success.main" fontWeight="bold">
                  ${data.margen_promedio.toLocaleString()}
                </Typography>
              </Box>
              <Box py={2}>
                <Typography variant="body2" color="text.secondary">Ticket Promedio</Typography>
                <Typography variant="h5" fontWeight="bold">
                  ${data.ventas_mes.count > 0 ? (data.ventas_mes.total / data.ventas_mes.count).toLocaleString(undefined, {maximumFractionDigits: 0}) : 0}
                </Typography>
              </Box>
              <Box py={2}>
                <Typography variant="body2" color="text.secondary">Tasa de Cobro</Typography>
                <Typography variant="h5" color="info.main" fontWeight="bold">
                  {data.ventas_mes.total > 0 ? ((data.pagos_mes.total / data.ventas_mes.total) * 100).toFixed(1) : 0}%
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}