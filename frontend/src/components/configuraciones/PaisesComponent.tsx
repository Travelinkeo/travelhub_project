'use client';

import { useState } from 'react';
import { Box, Button, CircularProgress, Alert } from '@mui/material';
import { DataGrid, GridColDef, GridRenderCellParams } from '@mui/x-data-grid';

import { useApi } from '@/hooks/useApi';
import { Pais } from '@/types/api';
import { apiMutate } from '@/lib/api';

const PaisesComponent = () => {
  const { data: paises, isLoading, error, mutate } = useApi<Pais[]>('/api/paises/');

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedItem, setSelectedItem] = useState<Pais | null>(null);

  const handleOpenModal = (item: Pais | null) => {
    setSelectedItem(item);
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setSelectedItem(null);
  };

  const handleSave = async (data: Partial<Pais>) => {
    const isNew = !data.id_pais;
    const endpoint = isNew ? '/api/paises/' : `/api/paises/${data.id_pais}/`;
    const method = isNew ? 'POST' : 'PUT';

    try {
      await apiMutate(endpoint, { method, body: data });
      mutate();
      handleCloseModal();
    } catch (e) {
      if (e instanceof Error) {
        alert(`Error al guardar:\n${e.message}`);
      } else {
        alert('Error al guardar: Ocurrió un error desconocido');
      }
    }
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm('¿Está seguro de que desea eliminar este país?')) {
      return;
    }

    try {
      await apiMutate(`/api/paises/${id}/`, { method: 'DELETE' });
      mutate();
    } catch (e) {
      if (e instanceof Error) {
        alert(e.message);
      } else {
        alert('Ocurrió un error desconocido');
      }
    }
  };

  const columns: GridColDef<Pais>[] = [
    { field: 'id_pais', headerName: 'ID', width: 90 },
    { field: 'codigo_iso_2', headerName: 'Código ISO 2', width: 120 },
    { field: 'codigo_iso_3', headerName: 'Código ISO 3', width: 120 },
    { field: 'nombre', headerName: 'Nombre', width: 200 },
    {
      field: 'actions',
      headerName: 'Acciones',
      width: 200,
      renderCell: (params: GridRenderCellParams<Pais>) => {
        if (!params.row) return null;
        return (
          <>
            <Button variant="outlined" size="small" onClick={() => handleOpenModal(params.row)} sx={{ mr: 1 }}>
              Editar
            </Button>
            <Button variant="outlined" size="small" color="error" onClick={() => handleDelete(params.row.id_pais!)}>
              Eliminar
            </Button>
          </>
        );
      },
    },
  ];

  if (isLoading) return <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}><CircularProgress /></Box>;
  if (error) return <Alert severity="error">Error al cargar países: {error.message}</Alert>;

  return (
    <Box>
      <Box sx={{ mb: 2, display: 'flex', justifyContent: 'flex-end' }}>
        <Button variant="contained" onClick={() => handleOpenModal(null)}>
          Crear Nuevo País
        </Button>
      </Box>
      <Box sx={{ height: '70vh', width: '100%' }}>
        <DataGrid
          rows={paises || []}
          columns={columns}
          loading={isLoading}
          getRowId={(row) => row.id_pais!}
          initialState={{
            pagination: { page: 0, pageSize: 25 },
            sorting: {
              sortModel: [{ field: 'id_pais', sort: 'desc' }],
            },
          }}
          checkboxSelection
        />
      </Box>
      {/* TODO: Crear PaisForm */}
      {/* <PaisForm
        open={isModalOpen}
        onClose={handleCloseModal}
        onSave={handleSave}
        pais={selectedItem}
      /> */}
    </Box>
  );
};

export default PaisesComponent;