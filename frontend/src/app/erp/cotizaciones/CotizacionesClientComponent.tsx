'use client';

import React, { useState, useMemo } from 'react';
import { DataGrid, GridColDef, GridRenderCellParams, GridValueGetterParams } from '@mui/x-data-grid';
import { Box, Button, Chip, CircularProgress, Alert, TextField } from '@mui/material';
import { useApi } from '@/hooks/useApi';
import { useDebounce } from '@/hooks/useDebounce';
import { Cotizacion, EstadoCotizacion, Paginated } from '@/types/api';
import { apiMutate } from '@/lib/api';
import CotizacionForm from './CotizacionForm';

// Helper to get chip color based on status
const getStatusChipColor = (status: EstadoCotizacion) => {
  switch (status) {
    case 'BOR': return 'default';
    case 'ENV': return 'info';
    case 'ACE': return 'success';
    case 'REC': return 'error';
    case 'VEN': return 'warning';
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
        placeholder="Buscar por número, cliente o destino..."
        sx={{ width: '50%' }}
      />
      <Button variant="contained" onClick={onAddNew}>
        Crear Cotización
      </Button>
    </Box>
  );
}

export default function CotizacionesClientComponent() {
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
    return `/api/cotizaciones/?${params.toString()}`;
  }, [page, pageSize, debouncedSearchTerm]);

  const { data, isLoading, error, mutate } = useApi<Paginated<Cotizacion>>(endpointUrl);
  
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingCotizacion, setEditingCotizacion] = useState<Cotizacion | null>(null);
  const [generatingPdfId, setGeneratingPdfId] = useState<number | null>(null);

  const handleCreateClick = () => {
    setEditingCotizacion(null);
    setIsFormOpen(true);
  };

  const handleEditClick = (cotizacion: Cotizacion) => {
    setEditingCotizacion(cotizacion);
    setIsFormOpen(true);
  };

  const handleCloseForm = () => {
    setIsFormOpen(false);
    setEditingCotizacion(null);
  };

  const handleSave = async (data: Partial<Cotizacion>) => {
    const isEditing = !!editingCotizacion;
    const endpoint = isEditing ? `/api/cotizaciones/${editingCotizacion.id_cotizacion}/` : '/api/cotizaciones/';
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

  const handleDelete = async (id: number) => {
    if (!window.confirm(`¿Está seguro de que desea eliminar la cotización ${id}?`)) return;
    try {
      await apiMutate(`/api/cotizaciones/${id}/`, { method: 'DELETE' });
      mutate();
    } catch (e) {
      alert(`Error al eliminar: ${e instanceof Error ? e.message : 'Error desconocido'}`);
    }
  };

  const handleGeneratePdf = async (id: number) => {
    setGeneratingPdfId(id);
    try {
      await apiMutate(`/api/cotizaciones/${id}/generar-pdf/`, { method: 'POST' });
      mutate();
    } catch (e) {
      alert(`Error al generar el PDF: ${e instanceof Error ? e.message : 'Error desconocido'}`);
    }
    setGeneratingPdfId(null);
  };

  const columns: GridColDef<Cotizacion>[] = [
    { field: 'numero_cotizacion', headerName: 'Número', width: 180 },
    {
      field: 'cliente',
      headerName: 'Cliente',
      flex: 1,
      valueGetter: (params: GridValueGetterParams<Cotizacion>) => 
        params.row.cliente_detalle?.get_nombre_completo || 'N/A',
    },
    { field: 'destino', headerName: 'Destino', flex: 1 },
    {
        field: 'fecha_emision',
        headerName: 'Fecha Emisión',
        width: 120,
        valueGetter: (params: GridValueGetterParams<Cotizacion>) => 
            new Date(params.row.fecha_emision).toLocaleDateString(),
    },
    {
        field: 'total_cotizado',
        headerName: 'Total',
        width: 150,
        valueGetter: (params: GridValueGetterParams<Cotizacion>) => 
            `$ ${parseFloat(params.row.total_cotizado).toFixed(2)}`,
    },
    {
      field: 'estado',
      headerName: 'Estado',
      width: 150,
      renderCell: (params) => (
        <Chip 
          label={params.row.estado}
          color={getStatusChipColor(params.row.estado as EstadoCotizacion)}
          size="small"
        />
      ),
    },
    {
      field: 'actions',
      headerName: 'Acciones',
      width: 350,
      sortable: false,
      renderCell: (params: GridRenderCellParams<Cotizacion>) => {
        const isGenerating = generatingPdfId === params.row.id_cotizacion;
        return (
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Button variant="outlined" size="small" onClick={() => handleEditClick(params.row)}>
              Ver/Editar
            </Button>
            {params.row.archivo_pdf && (
              <Button 
                variant="outlined" 
                size="small" 
                color="secondary"
                href={params.row.archivo_pdf}
                target="_blank"
                rel="noopener noreferrer"
              >
                Ver PDF
              </Button>
            )}
            <Button 
              variant="outlined" 
              size="small" 
              color="success"
              onClick={() => handleGeneratePdf(params.row.id_cotizacion)}
              disabled={isGenerating}
            >
              {isGenerating ? <CircularProgress size={20} /> : 'Generar PDF'}
            </Button>
            <Button 
              variant="outlined" 
              size="small" 
              color="error" 
              onClick={() => handleDelete(params.row.id_cotizacion)}
            >
              Eliminar
            </Button>
          </Box>
        );
      },
    },
  ];

  if (error) return <Alert severity="error">Error al cargar las cotizaciones: {error.message}</Alert>;

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '85vh', width: '100%' }}>
      <DataGrid
        rows={data?.results || []}
        columns={columns}
        loading={isLoading}
        getRowId={(row) => row.id_cotizacion}
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
        slots={{
          toolbar: CustomToolbar,
        }}
        slotProps={{
          toolbar: {
            onSearch: setSearchTerm,
            searchTerm: searchTerm,
            onAddNew: handleCreateClick,
          },
        }}
        checkboxSelection
        disableRowSelectionOnClick
      />

      {isFormOpen && (
        <CotizacionForm 
          open={isFormOpen}
          onClose={handleCloseForm}
          onSave={handleSave}
          cotizacion={editingCotizacion}
        />
      )}
    </Box>
  );
}