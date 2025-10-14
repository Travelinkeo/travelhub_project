import DashboardMetricas from '@/components/Dashboard/DashboardMetricas';
import CotizacionesPanel from '@/components/Dashboard/CotizacionesPanel';
import { Box, Typography, Grid } from '@mui/material';

export default function DashboardPage() {
  return (
    <Box>
      <Typography variant="h3" component="h1" gutterBottom sx={{ p: 3, pb: 0 }}>
        Dashboard TravelHub
      </Typography>
      <DashboardMetricas />
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