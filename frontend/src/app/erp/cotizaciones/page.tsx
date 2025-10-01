import CotizacionesClientComponent from './CotizacionesClientComponent';
import { Box, Typography } from '@mui/material';

export default function CotizacionesPage() {
  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        Gestión de Cotizaciones
      </Typography>
      <CotizacionesClientComponent />
    </Box>
  );
}
