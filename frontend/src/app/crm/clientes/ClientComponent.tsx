'use client';

import React, { useState, useMemo } from 'react';
import { Box, Button, CircularProgress, Alert, TextField } from '@mui/material';
import { DataGrid, GridColDef, GridRenderCellParams } from '@mui/x-data-grid';

// Components
import ClienteForm from './ClienteForm';
import { PassportModal } from '@/components/PassportModal';

// Hooks and types
import { useApi } from '@/hooks/useApi';
import { useDebounce } from '@/hooks/useDebounce';
import { Cliente, Paginated } from '@/types/api';
import { apiMutate } from '@/lib/api';

// Toolbar is now a separate component rendered outside the DataGrid
function CustomToolbar(
  { onSearch, searchTerm, onAddNew, onScanPassport }
  : { onSearch: (term: string) => void, searchTerm: string, onAddNew: () => void, onScanPassport: () => void }
) {
  return (
    <Box sx={{ p: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #e0e0e0' }}>
      <TextField
        variant="outlined"
        value={searchTerm}
        onChange={(e) => onSearch(e.target.value)}
        placeholder="Buscar cliente..."
        sx={{ width: '40%' }}
      />
      <Box sx={{ display: 'flex', gap: 1 }}>
        <Button variant="outlined" onClick={onScanPassport}>
          📸 Escanear Pasaporte
        </Button>
        <Button variant="contained" onClick={onAddNew}>
          Crear Nuevo Cliente
        </Button>
      </Box>
    </Box>
  );
}

const ClientesClientComponent = () => {
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
    return `/api/clientes/?${params.toString()}`;
  }, [page, pageSize, debouncedSearchTerm]);

  const { data, isLoading, error, mutate } = useApi<Paginated<Cliente>>(endpointUrl);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedClient, setSelectedClient] = useState<Cliente | null>(null);
  const [isPassportModalOpen, setIsPassportModalOpen] = useState(false);

  const handleOpenModal = (cliente: Cliente | null) => {
    setSelectedClient(cliente);
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setSelectedClient(null);
  };

  const handleSave = async (clienteData: Partial<Cliente>) => {
    const isNew = !clienteData.id_cliente;
    const endpoint = isNew ? `/api/clientes/` : `/api/clientes/${clienteData.id_cliente}/`;
    const method = isNew ? 'POST' : 'PUT';

    try {
      console.log('Enviando datos:', clienteData);
      await apiMutate(endpoint, { method, body: clienteData });
      mutate();
      handleCloseModal();
    } catch (e: any) {
      console.error('Error del servidor:', e);
      console.error('Detalles del error:', e.response);
      alert(JSON.stringify(e.response || e.message, null, 2));
    }
  };

  const handleDelete = async (idCliente: number) => {
    if (!window.confirm('¿Está seguro de que desea eliminar este cliente?')) return;

    try {
      await apiMutate(`/api/clientes/${idCliente}/`, { method: 'DELETE' });
      mutate();
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Ocurrió un error desconocido');
    }
  };

  const columns: GridColDef<Cliente>[] = [
    { field: 'id_cliente', headerName: 'ID', width: 90 },
    {
      field: 'nombre',
      headerName: 'Nombre / Empresa',
      flex: 1,
      valueGetter: (params) => 
        params.row.tipo_cliente === 'EMP'
          ? params.row.nombre_empresa || ''
          : `${params.row.nombres || ''} ${params.row.apellidos || ''}`.trim(),
    },
    { field: 'email', headerName: 'Email', flex: 1 },
    { field: 'telefono_principal', headerName: 'Teléfono', width: 150 },
    {
      field: 'actions',
      headerName: 'Acciones',
      width: 200,
      sortable: false,
      renderCell: (params: GridRenderCellParams<Cliente>) => (
        <Box>
          <Button variant="outlined" size="small" onClick={() => handleOpenModal(params.row)} sx={{ mr: 1 }}>
            Editar
          </Button>
          <Button variant="outlined" size="small" color="error" onClick={() => handleDelete(params.row.id_cliente!)}>
            Eliminar
          </Button>
        </Box>
      ),
    },
  ];

  if (error) return <Alert severity="error">Error al cargar clientes: {error.message}</Alert>;

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '85vh', width: '100%' }}>
      <CustomToolbar 
        onSearch={setSearchTerm} 
        searchTerm={searchTerm} 
        onAddNew={() => handleOpenModal(null)}
        onScanPassport={() => setIsPassportModalOpen(true)}
      />
      <Box sx={{ flexGrow: 1, width: '100%' }}>
        <DataGrid
          rows={data?.results || []}
          columns={columns}
          loading={isLoading}
          getRowId={(row) => row.id_cliente!}
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
          checkboxSelection
          disableRowSelectionOnClick
        />
      </Box>
      <ClienteForm
        open={isModalOpen}
        onClose={handleCloseModal}
        onSave={handleSave}
        cliente={selectedClient}
      />
      <PassportModal
        isOpen={isPassportModalOpen}
        onClose={() => setIsPassportModalOpen(false)}
        onClientCreated={(clientId) => {
          setIsPassportModalOpen(false);
          mutate(); // Refresh the client list
          alert(`Cliente creado exitosamente con ID: ${clientId}`);
        }}
      />
    </Box>
  );
};

export default ClientesClientComponent;