'use client';

import { useState } from 'react';
import { Box, Typography, Tabs, Tab } from '@mui/material';
import PerfilAgencia from '@/components/configuraciones/PerfilAgencia';
import GestorUsuarios from '@/components/configuraciones/GestorUsuarios';

export default function AgenciaConfigPage() {
  const [tab, setTab] = useState(0);

  return (
    <Box p={3}>
      <Typography variant="h4" gutterBottom>
        Configuración de Agencia
      </Typography>
      
      <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 3 }}>
        <Tab label="Perfil de Agencia" />
        <Tab label="Usuarios" />
      </Tabs>

      {tab === 0 && <PerfilAgencia />}
      {tab === 1 && <GestorUsuarios />}
    </Box>
  );
}
