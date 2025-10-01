'use client';

import DashboardStats from '@/components/Dashboard/DashboardStats';
import CotizacionesPanel from '@/components/Dashboard/CotizacionesPanel';
import { Box, Typography, Grid } from '@mui/material';

export default function HomePage() {
  return (
    <Box>
      <Typography variant="h3" component="h1" gutterBottom sx={{ p: 3, pb: 0 }} color="text.primary">
        TravelHub - Dashboard Ejecutivo
      </Typography>
      <DashboardStats />
      <Box p={3}>
        <Grid container spacing={3}>
          <Grid item xs={12}>
            <CotizacionesPanel />
          </Grid>
        </Grid>
      </Box>
    </Box>
  );
}