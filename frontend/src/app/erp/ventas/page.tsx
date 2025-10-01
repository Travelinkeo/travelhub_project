import VentasClientComponent from './VentasClientComponent';
import { Box, Typography } from '@mui/material';

export default function VentasPage() {
  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        Gestión de Ventas y Reservas
      </Typography>
      <VentasClientComponent />
    </Box>
  );
}