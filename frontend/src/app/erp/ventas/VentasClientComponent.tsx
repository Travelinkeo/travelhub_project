'use client';

import React, { useState, useMemo } from 'react';
import { DataGrid, GridColDef, GridRenderCellParams, GridValueGetterParams } from '@mui/x-data-grid';
import { Box, Button, Chip, CircularProgress, Alert, TextField } from '@mui/material';
import { useRouter } from 'next/navigation';
import { useApi } from '@/hooks/useApi';
import { useDebounce } from '@/hooks/useDebounce';
import { Venta, EstadoVenta, Paginated } from '@/types/api';
import { apiMutate } from '@/lib/api';
import VentaForm from './VentaForm'; // Assuming this form exists

// Helper to get chip color based on status
const getStatusChipColor = (status: EstadoVenta) => {
  switch (status) {
    case 'PEN': return 'warning';
    case 'PAR': return 'info';
    case 'PAG':
    case 'CNF':
    case 'COM': 
      return 'success';
    case 'CAN': return 'error';
    default: return 'default';
  }
};

function CustomToolbar(
  { onSearch, searchTerm, onAddNew }
  : { onSearch: (term: string) => void, searchTerm: string, onAddNew: () => void }
) {
  return (
    <Box sx={{ p: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #e0e0e0' }}>
      <TextField
        variant="outlined"
        value={searchTerm}
        onChange={(e) => onSearch(e.target.value)}
        placeholder="Buscar por localizador o cliente..."
        sx={{ width: '50%' }}
      />
      <Button 
        variant="contained" 
        onClick={() => {
          console.log('Crear Venta clicked');
          onAddNew();
        }}
      >
        Crear Nueva Venta
      </Button>
    </Box>
  );
}

export default function VentasClientComponent() {
  const router = useRouter();
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(25);
  const [searchTerm, setSearchTerm] = useState('');
  const debouncedSearchTerm = useDebounce(searchTerm, 500);

  const endpointUrl = useMemo(() => {
    const params = new URLSearchParams();
    params.append('page', (page + 1).toString());
    if (pageSize !== 25) {
      params.append('page_size', pageSize.toString());
    }
    if (debouncedSearchTerm) {
      params.append('search', debouncedSearchTerm);
    }
    return `/api/ventas/?${params.toString()}`;
  }, [page, pageSize, debouncedSearchTerm]);

  const { data, isLoading, error, mutate } = useApi<Paginated<Venta>>(endpointUrl);
  
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingVenta, setEditingVenta] = useState<Venta | null>(null);

  const handleCreateClick = () => {
    router.push('/erp/ventas/nueva');
  };

  const handleEditClick = (venta: Venta) => {
    setEditingVenta(venta);
    setIsFormOpen(true);
  };

  const handleCloseForm = () => {
    setIsFormOpen(false);
    setEditingVenta(null);
  };

  const handleSave = async (data: Partial<Venta>) => {
    const isEditing = !!editingVenta;
    const endpoint = isEditing ? `/api/ventas/${editingVenta.id_venta}/` : '/api/ventas/';
    const method = isEditing ? 'PUT' : 'POST';

    try {
      await apiMutate(endpoint, { method, body: data });
      mutate();
      handleCloseForm();
    } catch (e) {
      alert(`Error al guardar: ${e instanceof Error ? e.message : 'Error desconocido'}`);
      throw e;
    }
  };

  const columns: GridColDef<Venta>[] = [
    { field: 'id_venta', headerName: 'ID', width: 90 },
    { field: 'localizador', headerName: 'Localizador', width: 130 },
    {
      field: 'cliente',
      headerName: 'Cliente',
      flex: 1,
      valueGetter: (params: GridValueGetterParams<Venta>) => 
        params.row.cliente_detalle?.get_nombre_completo || 'N/A',
    },
    {
        field: 'fecha_venta',
        headerName: 'Fecha',
        width: 120,
        valueGetter: (params: GridValueGetterParams<Venta>) => 
            new Date(params.row.fecha_venta).toLocaleDateString(),
    },
    {
        field: 'total_venta',
        headerName: 'Total',
        width: 150,
        valueGetter: (params: GridValueGetterParams<Venta>) => 
            `${params.row.moneda_detalle?.codigo_iso || ''} ${parseFloat(params.row.total_venta).toFixed(2)}`,
    },
    {
      field: 'estado',
      headerName: 'Estado',
      width: 180,
      renderCell: (params) => (
        <Chip 
          label={params.row.estado}
          color={getStatusChipColor(params.row.estado as EstadoVenta)}
          size="small"
        />
      ),
    },
    {
      field: 'actions',
      headerName: 'Acciones',
      width: 200,
      sortable: false,
      renderCell: (params: GridRenderCellParams<Venta>) => (
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button variant="outlined" size="small" onClick={() => handleEditClick(params.row)}>
            Editar
          </Button>
          <Button 
            variant="outlined" 
            size="small" 
            color="error" 
            onClick={async () => {
              if (!window.confirm(`¿Eliminar Venta ID: ${params.row.id_venta}?`)) return;
              await apiMutate(`/api/ventas/${params.row.id_venta}/`, { method: 'DELETE' });
              mutate();
            }}
          >
            Eliminar
          </Button>
        </Box>
      ),
    },
  ];

  if (error) return <Alert severity="error">Error al cargar las ventas: {error.message}</Alert>;

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '85vh', width: '100%' }}>
      <CustomToolbar 
        onSearch={setSearchTerm} 
        searchTerm={searchTerm} 
        onAddNew={handleCreateClick} 
      />
      <DataGrid
        rows={data?.results || []}
        columns={columns}
        loading={isLoading}
        getRowId={(row) => row.id_venta}
        rowCount={data?.count || 0}
        pagination
        paginationMode="server"
        onPaginationModelChange={(model) => {
          setPage(model.page);
          setPageSize(model.pageSize);
        }}
        initialState={{
          pagination: { paginationModel: { page, pageSize } },
        }}
        pageSizeOptions={[10, 25, 50]}

        checkboxSelection
        disableRowSelectionOnClick
      />

      {isFormOpen && (
        <VentaForm 
          open={isFormOpen}
          onClose={handleCloseForm}
          onSave={handleSave}
          venta={editingVenta}
        />
      )}
    </Box>
  );
}