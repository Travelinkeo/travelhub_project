'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, Typography, Grid, Box, Alert, Chip } from '@mui/material';
import { TrendingUp, AttachMoney, Warning, CheckCircle } from '@mui/icons-material';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://127.0.0.1:8000';

function getAuthHeaders() {
  const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null;
  return token ? { 'Authorization': `Bearer ${token}` } : {};
}

interface Metricas {
  resumen: {
    total_ventas: number;
    monto_total: number;
    saldo_pendiente: number;
    margen_estimado: number;
    co2_estimado_kg: number;
  };
  ventas_por_estado: Array<{ estado: string; count: number; total: number }>;
  top_clientes: Array<{
    cliente__id_cliente: number;
    cliente__nombres: string;
    cliente__apellidos: string;
    total_compras: number;
    num_ventas: number;
  }>;
  liquidaciones_pendientes: { count: number; total: number };
  facturas_pendientes: { count: number; total: number };
  tendencia_semanal: Array<{ fecha: string; total: number; count: number }>;
}

interface Alertas {
  alertas: Array<{
    tipo: string;
    count: number;
    mensaje: string;
    severidad: string;
  }>;
}

export default function DashboardMetricas() {
  const [metricas, setMetricas] = useState<Metricas | null>(null);
  const [alertas, setAlertas] = useState<Alertas | null>(null);

  useEffect(() => {
    const cargarDatos = async () => {
      try {
        const [metricasRes, alertasRes] = await Promise.all([
          fetch(`${API_BASE_URL}/api/dashboard/metricas/`, { headers: getAuthHeaders() }),
          fetch(`${API_BASE_URL}/api/dashboard/alertas/`, { headers: getAuthHeaders() })
        ]);
        const metricas = await metricasRes.json();
        const alertas = await alertasRes.json();
        setMetricas(metricas);
        setAlertas(alertas);
      } catch (error) {
        console.error('Error cargando dashboard:', error);
      }
    };
    cargarDatos();
  }, []);

  if (!metricas) return <Typography>Cargando...</Typography>;

  return (
    <Box p={3}>
      {/* Alertas */}
      {alertas?.alertas.map((alerta, idx) => (
        <Alert 
          key={idx} 
          severity={alerta.severidad as any} 
          sx={{ mb: 2 }}
          icon={alerta.severidad === 'error' ? <Warning /> : undefined}
        >
          {alerta.mensaje}
        </Alert>
      ))}

      {/* KPIs Principales */}
      <Grid container spacing={3} mb={4}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>Total Ventas</Typography>
              <Typography variant="h4" color="primary">{metricas.resumen.total_ventas}</Typography>
              <Typography variant="h6">${metricas.resumen.monto_total.toLocaleString()}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>Saldo Pendiente</Typography>
              <Typography variant="h4" color="warning.main">
                ${metricas.resumen.saldo_pendiente.toLocaleString()}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>Margen Estimado</Typography>
              <Typography variant="h4" color="success.main">
                ${metricas.resumen.margen_estimado.toLocaleString()}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>CO2 Estimado</Typography>
              <Typography variant="h4">{metricas.resumen.co2_estimado_kg.toFixed(0)} kg</Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Ventas por Estado */}
      <Grid container spacing={3} mb={4}>
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Ventas por Estado</Typography>
              {metricas.ventas_por_estado.map((item) => (
                <Box key={item.estado} display="flex" justifyContent="space-between" py={1}>
                  <Chip label={item.estado} size="small" />
                  <Box textAlign="right">
                    <Typography variant="body2">{item.count} ventas</Typography>
                    <Typography variant="body2" fontWeight="bold">
                      ${item.total.toLocaleString()}
                    </Typography>
                  </Box>
                </Box>
              ))}
            </CardContent>
          </Card>
        </Grid>

        {/* Top Clientes */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Top Clientes</Typography>
              {metricas.top_clientes.slice(0, 5).map((cliente) => (
                <Box key={cliente.cliente__id_cliente} display="flex" justifyContent="space-between" py={1}>
                  <Box>
                    <Typography variant="body2" fontWeight="bold">
                      {cliente.cliente__nombres} {cliente.cliente__apellidos}
                    </Typography>
                    <Typography variant="caption" color="textSecondary">
                      {cliente.num_ventas} ventas
                    </Typography>
                  </Box>
                  <Typography variant="body2" fontWeight="bold">
                    ${cliente.total_compras.toLocaleString()}
                  </Typography>
                </Box>
              ))}
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Pendientes */}
      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Liquidaciones Pendientes</Typography>
              <Typography variant="h4" color="warning.main">
                {metricas.liquidaciones_pendientes.count}
              </Typography>
              <Typography variant="body2">
                Total: ${metricas.liquidaciones_pendientes.total.toLocaleString()}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Facturas Pendientes</Typography>
              <Typography variant="h4" color="error.main">
                {metricas.facturas_pendientes.count}
              </Typography>
              <Typography variant="body2">
                Total: ${metricas.facturas_pendientes.total.toLocaleString()}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}
