import FacturasClientComponent from './FacturasClientComponent';
import { Box, Typography } from '@mui/material';

export default function FacturasPage() {
  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        Gestión de Facturas
      </Typography>
      <FacturasClientComponent />
    </Box>
  );
}