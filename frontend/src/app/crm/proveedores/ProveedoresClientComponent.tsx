'use client';

import React, { useState, useMemo } from 'react';
import { Box, Button, CircularProgress, Alert, TextField, Chip } from '@mui/material';
import { DataGrid, GridColDef, GridRenderCellParams } from '@mui/x-data-grid';

// Components
import ProveedorForm from './ProveedorForm';

// Hooks and types
import { useApi } from '@/hooks/useApi';
import { useDebounce } from '@/hooks/useDebounce';
import { Proveedor, Paginated } from '@/types/api';
import { apiMutate } from '@/lib/api';

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
        placeholder="Buscar proveedor..."
        sx={{ width: '50%' }}
      />
      <Button variant="contained" onClick={onAddNew}>
        Crear Nuevo Proveedor
      </Button>
    </Box>
  );
}

const ProveedoresClientComponent = () => {
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
    return `/api/proveedores/?${params.toString()}`;
  }, [page, pageSize, debouncedSearchTerm]);

  const { data, isLoading, error, mutate } = useApi<Paginated<Proveedor>>(endpointUrl);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedProveedor, setSelectedProveedor] = useState<Proveedor | null>(null);

  const handleOpenModal = (proveedor: Proveedor | null) => {
    setSelectedProveedor(proveedor);
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setSelectedProveedor(null);
  };

  const handleSave = async (proveedorData: Partial<Proveedor>) => {
    const isNew = !proveedorData.id_proveedor;
    const endpoint = isNew ? `/api/proveedores/` : `/api/proveedores/${proveedorData.id_proveedor}/`;
    const method = isNew ? 'POST' : 'PUT';

    try {
      await apiMutate(endpoint, { method, body: proveedorData });
      mutate();
      handleCloseModal();
    } catch (e) {
      alert(e instanceof Error ? `Error al guardar:\n${e.message}` : 'Ocurrió un error desconocido');
    }
  };

  const handleDelete = async (idProveedor: number) => {
    if (!window.confirm('¿Está seguro de que desea eliminar este proveedor?')) return;

    try {
      await apiMutate(`/api/proveedores/${idProveedor}/`, { method: 'DELETE' });
      mutate();
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Ocurrió un error desconocido');
    }
  };

  const columns: GridColDef<Proveedor>[] = [
    { field: 'id_proveedor', headerName: 'ID', width: 90 },
    { field: 'nombre', headerName: 'Nombre', flex: 1 },
    { field: 'tipo_proveedor', headerName: 'Tipo', width: 150 },
    { field: 'contacto_email', headerName: 'Email de Contacto', flex: 1 },
    {
      field: 'activo',
      headerName: 'Activo',
      width: 100,
      renderCell: (params) => (
        params.row ? <Chip label={params.value ? 'Sí' : 'No'} color={params.value ? 'success' : 'error'} size="small" /> : null
      ),
    },
    {
      field: 'actions',
      headerName: 'Acciones',
      width: 200,
      sortable: false,
      renderCell: (params: GridRenderCellParams<Proveedor>) => (
        params.row ? (
          <Box>
            <Button variant="outlined" size="small" onClick={() => handleOpenModal(params.row)} sx={{ mr: 1 }}>
              Editar
            </Button>
            <Button variant="outlined" size="small" color="error" onClick={() => handleDelete(params.row.id_proveedor!)}>
              Eliminar
            </Button>
          </Box>
        ) : null
      ),
    },
  ];

  if (error) return <Alert severity="error">Error al cargar proveedores: {error.message}</Alert>;

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '85vh', width: '100%' }}>
      <CustomToolbar 
        onSearch={setSearchTerm} 
        searchTerm={searchTerm} 
        onAddNew={() => handleOpenModal(null)} 
      />
      <Box sx={{ flexGrow: 1, width: '100%' }}>
        <DataGrid
          rows={data?.results || []}
          columns={columns}
          loading={isLoading}
          getRowId={(row) => row.id_proveedor!}
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
      <ProveedorForm
        open={isModalOpen}
        onClose={handleCloseModal}
        onSave={handleSave}
        proveedor={selectedProveedor}
      />
    </Box>
  );
};

export default ProveedoresClientComponent;