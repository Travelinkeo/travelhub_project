'use client';

import React, { useState, useMemo } from 'react';
import { DataGrid, GridColDef, GridRenderCellParams } from '@mui/x-data-grid';
import { Box, Button, Chip, CircularProgress, Alert, TextField } from '@mui/material';
import { useApi } from '@/hooks/useApi';
import { useDebounce } from '@/hooks/useDebounce';
import { BoletoImportado, EstadoParseoBoleto, Paginated } from '@/types/api';
import { apiMutate } from '@/lib/api';
import BoletoImportModal from './BoletoImportModal';
import BoletoImportadoForm from './BoletoImportadoForm';
import BoletoManualForm from './BoletoManualForm';

// Helper to get chip color based on status
const getStatusChipColor = (status: EstadoParseoBoleto) => {
  switch (status) {
    case 'PEN': return 'warning';
    case 'PRO': return 'info';
    case 'COM': return 'success';
    case 'ERR': return 'error';
    default: return 'default';
  }
};

function CustomToolbar(
  { onSearch, searchTerm, onAddNew, onAddManual }
  : { onSearch: (term: string) => void, searchTerm: string, onAddNew: () => void, onAddManual: () => void }
) {
  return (
    <Box sx={{ p: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #e0e0e0' }}>
      <TextField
        variant="outlined"
        value={searchTerm}
        onChange={(e) => onSearch(e.target.value)}
        placeholder="Buscar boleto..."
        sx={{ width: '50%' }}
      />
      <Box sx={{ display: 'flex', gap: 1 }}>
        <Button variant="contained" color="secondary" onClick={onAddManual}>
          Ingresar Boleto Manualmente
        </Button>
        <Button variant="contained" onClick={onAddNew}>
          Importar Boleto
        </Button>
      </Box>
    </Box>
  );
}

export default function BoletosImportadosClientComponent() {
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
    return `/api/boletos-importados/?${params.toString()}`;
  }, [page, pageSize, debouncedSearchTerm]);

  const { data, isLoading, error, mutate } = useApi<Paginated<BoletoImportado>>(endpointUrl);
  
  // State for modals
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);
  const [isManualFormOpen, setIsManualFormOpen] = useState(false);
  const [editingBoleto, setEditingBoleto] = useState<BoletoImportado | null>(null);
  const [viewingBoleto, setViewingBoleto] = useState<BoletoImportado | null>(null);

  // Handlers
  const handleManualCreateClick = () => {
    setEditingBoleto(null);
    setIsManualFormOpen(true);
  };
  const handleCloseManualForm = () => setIsManualFormOpen(false);
  const handleSaveManual = async (boletoData: Partial<BoletoImportado>) => {
    try {
      await apiMutate('/api/boletos-importados/', { method: 'POST', body: boletoData });
      mutate();
      handleCloseManualForm();
    } catch (error) {
      alert(`Error al guardar el boleto: ${error instanceof Error ? error.message : 'Error desconocido'}`);
    }
  };

  const handleEditClick = (boleto: BoletoImportado) => setEditingBoleto(boleto);
  const handleCloseEditForm = () => setEditingBoleto(null);
  const handleSaveEdit = async (boletoData: Partial<BoletoImportado>) => {
    if (!editingBoleto) return;
    const endpoint = `/api/boletos-importados/${editingBoleto.id_boleto_importado}/`;
    await apiMutate(endpoint, { method: 'PUT', body: boletoData });
    mutate();
  };

  const handleViewClick = (boleto: BoletoImportado) => setViewingBoleto(boleto);
  const handleCloseViewForm = () => setViewingBoleto(null);

  const columns: GridColDef<BoletoImportado>[] = [
    { field: 'id_boleto_importado', headerName: 'ID', width: 90 },
    { field: 'localizador_pnr', headerName: 'Localizador', width: 130 },
    { field: 'nombre_pasajero_procesado', headerName: 'Pasajero', flex: 1 },
    { field: 'numero_boleto', headerName: 'N° Boleto', width: 180 },
    { field: 'aerolinea_emisora', headerName: 'Aerolínea', width: 150 },
    {
      field: 'estado_parseo',
      headerName: 'Estado',
      width: 150,
      renderCell: (params) => (
        <Chip 
          label={params.value}
          color={getStatusChipColor(params.value as EstadoParseoBoleto)}
          size="small"
        />
      ),
    },
    {
      field: 'actions',
      headerName: 'Acciones',
      width: 320,
      sortable: false,
      renderCell: (params: GridRenderCellParams<BoletoImportado>) => (
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button size="small" variant="outlined" onClick={() => handleViewClick(params.row)}>Ver</Button>
          <Button size="small" variant="outlined" onClick={() => handleEditClick(params.row)}>Editar</Button>
          {params.row.archivo_pdf_generado && (
            <Button size="small" variant="outlined" color="secondary" href={params.row.archivo_pdf_generado} target="_blank">Ver PDF</Button>
          )}
          <Button 
            size="small" 
            variant="outlined" 
            color="error" 
            onClick={async () => {
              if (!window.confirm(`¿Eliminar boleto ${params.row.id_boleto_importado}?`)) return;
              await apiMutate(`/api/boletos-importados/${params.row.id_boleto_importado}/`, { method: 'DELETE' });
              mutate();
            }}
          >
            Eliminar
          </Button>
        </Box>
      ),
    },
  ];

  if (error) return <Alert severity="error">Error al cargar los boletos: {error.message}</Alert>;

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '85vh', width: '100%' }}>
      <CustomToolbar 
        onSearch={setSearchTerm} 
        searchTerm={searchTerm} 
        onAddNew={() => setIsImportModalOpen(true)} 
        onAddManual={handleManualCreateClick}
      />
      <Box sx={{ flexGrow: 1, width: '100%' }}>
        <DataGrid
          rows={data?.results || []}
          columns={columns}
          loading={isLoading}
          getRowId={(row) => row.id_boleto_importado}
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
          pageSizeOptions={[10, 25, 50, 100]}
          checkboxSelection
          disableRowSelectionOnClick
        />
      </Box>
      
      <BoletoImportModal 
        open={isImportModalOpen}
        onClose={() => setIsImportModalOpen(false)}
        onUploadComplete={() => {
          setIsImportModalOpen(false);
          mutate();
        }}
      />

      <BoletoManualForm
        open={isManualFormOpen}
        onClose={handleCloseManualForm}
        onSave={handleSaveManual}
        boleto={null}
      />

      {editingBoleto && (
        <BoletoImportadoForm
          open={!!editingBoleto}
          onClose={handleCloseEditForm}
          onSave={handleSaveEdit}
          boleto={editingBoleto}
        />
      )}

      {viewingBoleto && (
        <BoletoImportadoForm
          open={!!viewingBoleto}
          onClose={handleCloseViewForm}
          boleto={viewingBoleto}
          readOnly={true}
        />
      )}
    </Box>
  );
}