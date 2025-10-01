'use client';

import React, { useState, useMemo } from 'react';
import { DataGrid, GridColDef, GridRenderCellParams } from '@mui/x-data-grid';
import { Box, Button, Chip, CircularProgress, Alert, TextField, IconButton } from '@mui/material';
import PictureAsPdfIcon from '@mui/icons-material/PictureAsPdf';
import { useApi } from '@/hooks/useApi';
import { useDebounce } from '@/hooks/useDebounce';
import { Factura, EstadoFactura, Paginated } from '@/types/api';
import { apiMutate } from '@/lib/api';
import FacturaForm from './FacturaForm';

// Helper to get chip color based on status
const getStatusChipColor = (status: EstadoFactura) => {
  switch (status) {
    case 'PAG': return 'success';
    case 'PAR':
    case 'EMI': return 'warning';
    case 'VEN':
    case 'ANU': return 'error';
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
        placeholder="Buscar por N° Factura o Cliente..."
        sx={{ width: '50%' }}
      />
      <Button variant="contained" onClick={onAddNew}>
        Crear Factura
      </Button>
    </Box>
  );
}

export default function FacturasClientComponent() {
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(25);
  const [searchTerm, setSearchTerm] = useState('');
  const debouncedSearchTerm = useDebounce(searchTerm, 500);

  const endpointUrl = useMemo(() => {
    const params = new URLSearchParams();
    params.append('page', (page + 1).toString());
    params.append('page_size', pageSize.toString());
    if (debouncedSearchTerm) {
      params.append('search', debouncedSearchTerm);
    }
    return `/api/facturas/?${params.toString()}`;
  }, [page, pageSize, debouncedSearchTerm]);

  const { data, isLoading, error, mutate } = useApi<Paginated<Factura>>(endpointUrl);
  
  // State for modals
  const [activeFactura, setActiveFactura] = useState<Partial<Factura> | null>(null);
  const [viewingFactura, setViewingFactura] = useState<Factura | null>(null);

  // Modal Handlers
  const handleCreate = () => setActiveFactura({});
  const handleEdit = (factura: Factura) => setActiveFactura(factura);
  const handleView = (factura: Factura) => setViewingFactura(factura);
  const handleCloseForms = () => {
    setActiveFactura(null);
    setViewingFactura(null);
  };

  const handleSave = async (facturaData: Partial<Factura>) => {
    const isNew = !facturaData.id_factura;
    const endpoint = isNew ? '/api/facturas/' : `/api/facturas/${facturaData.id_factura}/`;
    const method = isNew ? 'POST' : 'PUT';

    await apiMutate(endpoint, { method, body: facturaData });
    mutate();
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm(`¿Está seguro de que desea eliminar la factura ${id}?`)) return;
    await apiMutate(`/api/facturas/${id}/`, { method: 'DELETE' });
    mutate();
  };

  const columns: GridColDef<Factura>[] = [
    {
      field: 'archivo_pdf',
      headerName: 'PDF',
      width: 80,
      sortable: false,
      renderCell: (params) => (
        params.row && params.value ? (
          <IconButton color="primary" href={params.value as string} target="_blank" rel="noopener noreferrer" aria-label="Ver PDF">
            <PictureAsPdfIcon />
          </IconButton>
        ) : null
      ),
    },
    { field: 'numero_factura', headerName: 'Número Factura', width: 200 },
    {
      field: 'cliente_detalle',
      headerName: 'Cliente',
      flex: 1,
      valueGetter: (params) => params.row.cliente_detalle?.get_nombre_completo || 'N/A',
    },
    {
      field: 'estado',
      headerName: 'Estado',
      width: 150,
      renderCell: (params) => (
        params.row ? <Chip label={params.row.estado} color={getStatusChipColor(params.row.estado as EstadoFactura)} size="small" /> : null
      ),
    },
    {
      field: 'monto_total',
      headerName: 'Total',
      type: 'number',
      width: 150,
      valueGetter: (params) => `${params.row.moneda_detalle?.codigo_iso || ''} ${parseFloat(params.value || '0').toFixed(2)}`,
    },
    {
      field: 'saldo_pendiente',
      headerName: 'Saldo',
      type: 'number',
      width: 150,
      valueGetter: (params) => `${params.row.moneda_detalle?.codigo_iso || ''} ${parseFloat(params.value || '0').toFixed(2)}`,
    },
    {
      field: 'actions',
      headerName: 'Acciones',
      width: 250,
      sortable: false,
      renderCell: (params: GridRenderCellParams<Factura>) => (
        params.row ? (
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Button variant="outlined" size="small" onClick={() => handleView(params.row)}>Ver</Button>
            <Button variant="outlined" size="small" onClick={() => handleEdit(params.row)}>Editar</Button>
            <Button variant="outlined" size="small" color="error" onClick={() => handleDelete(params.row.id_factura)}>
              Eliminar
            </Button>
          </Box>
        ) : null
      ),
    },
  ];

  if (error) return <Alert severity="error">Error al cargar las facturas: {error.message}</Alert>;

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '85vh', width: '100%' }}>
      <CustomToolbar 
        onSearch={setSearchTerm} 
        searchTerm={searchTerm} 
        onAddNew={handleCreate} 
      />
      <Box sx={{ flexGrow: 1, width: '100%' }}>
        <DataGrid
          rows={data?.results || []}
          columns={columns}
          loading={isLoading}
          getRowId={(row) => row.id_factura}
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
      </Box>
      {activeFactura && (
        <FacturaForm
          open={!!activeFactura}
          onClose={handleCloseForms}
          onSave={handleSave}
          factura={activeFactura}
        />
      )}
      {viewingFactura && (
        <FacturaForm
          open={!!viewingFactura}
          onClose={handleCloseForms}
          factura={viewingFactura}
          readOnly={true}
        />
      )}
    </Box>
  );
}