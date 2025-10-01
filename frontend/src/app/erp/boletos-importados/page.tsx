import BoletosImportadosClientComponent from './BoletosImportadosClientComponent';
import { Box, Typography } from '@mui/material';

export default function BoletosImportadosPage() {
  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        Gestión de Boletos Importados
      </Typography>
      <BoletosImportadosClientComponent />
    </Box>
  );
}