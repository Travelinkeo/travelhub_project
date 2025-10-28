'use client';

import React, { useState } from 'react';
import { Box, Button, Typography } from '@mui/material';
import { useApi } from '@/hooks/useApi';
import FacturaConsolidadaForm from './FacturaConsolidadaForm';

export default function FacturasConsolidadasPage() {
  const { data, error, isLoading, mutate } = useApi<any>('/api/facturas-consolidadas/');
  const [openForm, setOpenForm] = useState(false);
  const [selectedFactura, setSelectedFactura] = useState<any>(null);

  const handleCreate = () => {
    setSelectedFactura(null);
    setOpenForm(true);
  };

  const handleSave = async (factura: any) => {
    const token = localStorage.getItem('auth_token');
    const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://127.0.0.1:8000';
    
    const response = await fetch(`${apiBaseUrl}/api/facturas-consolidadas/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify(factura)
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Error al guardar');
    }

    mutate();
  };

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
        <Typography variant="h4">Facturas Consolidadas</Typography>
        <Button variant="contained" onClick={handleCreate}>
          Nueva Factura
        </Button>
      </Box>

      {isLoading && <Typography>Cargando...</Typography>}
      {error && <Typography color="error">Error: {error.message}</Typography>}
      
      {data && (
        <Typography>
          Total de facturas: {data.results?.length || data.length || 0}
        </Typography>
      )}

      <FacturaConsolidadaForm
        open={openForm}
        onClose={() => setOpenForm(false)}
        onSave={handleSave}
        factura={selectedFactura}
      />
    </Box>
  );
}
