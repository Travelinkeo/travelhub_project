'use client';

import React, { useState, useMemo, useEffect } from 'react';
import { useApi } from '../hooks/useApi';
import { useApiCreate, useApiUpdate, useApiDelete } from '../hooks/api';
import { useDebounce } from '../hooks/useDebounce';
import { 
  Box, Button, Dialog, DialogTitle, DialogContent, DialogActions, TextField, 
  FormControl, InputLabel, Select, MenuItem, Table, TableBody, TableCell, 
  TableHead, TableRow, Paper, Skeleton, Alert, Pagination, Grid 
} from '@mui/material';
import { Paginated } from '@/types/api';

interface Column {
  key: string;
  label: string;
  render?: (value: any, item: any) => React.ReactNode;
}

interface Field {
  name: string;
  label: string;
  type: 'text' | 'number' | 'select';
  options?: { value: any; label: string }[];
  required?: boolean;
}

interface ApiTableProps {
  endpoint: string;
  columns: Column[];
  title?: string;
  fields: Field[];
}

const ApiTableComponent = ({ endpoint, columns, title, fields }: ApiTableProps) => {
  const [page, setPage] = useState(1);
  const [searchTerm, setSearchTerm] = useState('');
  const debouncedSearchTerm = useDebounce(searchTerm, 300);

  // Reset to page 1 whenever a search is performed
  useEffect(() => {
    if (debouncedSearchTerm) {
      setPage(1);
    }
  }, [debouncedSearchTerm]);

  const endpointUrl = useMemo(() => {
    const params = new URLSearchParams();
    params.append('page', page.toString());
    if (debouncedSearchTerm) {
      params.append('search', debouncedSearchTerm);
    }
    return `${endpoint}?${params.toString()}`;
  }, [endpoint, page, debouncedSearchTerm]);

  const { data, error, isLoading, mutate } = useApi<Paginated<any>>(endpointUrl);
  
  const { create, isCreating } = useApiCreate(endpoint);
  const [open, setOpen] = useState(false);
  const [editingItem, setEditingItem] = useState<any>(null);
  const [formData, setFormData] = useState<any>({});
  const [deleteId, setDeleteId] = useState<number | null>(null);
  const [updateId, setUpdateId] = useState<number | null>(null);

  const { deleteItem, isDeleting } = useApiDelete(endpoint, deleteId || 0);
  const { update, isUpdating } = useApiUpdate(endpoint, updateId || 0);

  const handleAdd = () => {
    setEditingItem(null);
    setFormData({});
    setOpen(true);
  };

  const handleEdit = (item: any) => {
    const idKey = Object.keys(item).find(k => k.startsWith('id')) || 'id';
    setEditingItem(item);
    setFormData({ ...item });
    setUpdateId(item[idKey]);
    setOpen(true);
  };

  const handleDelete = (item: any) => {
    if (confirm('¿Estás seguro de que quieres eliminar este elemento?')) {
      const idKey = Object.keys(item).find(k => k.startsWith('id')) || 'id';
      setDeleteId(item[idKey]);
    }
  };

  useEffect(() => {
    if (deleteId && !isDeleting) {
      deleteItem().then(() => {
        mutate();
        setDeleteId(null);
      }).catch(() => {
        alert('Error al eliminar');
        setDeleteId(null);
      });
    }
  }, [deleteId, isDeleting, deleteItem, mutate]);

  const handleSave = async () => {
    try {
      if (editingItem) {
        await update(formData);
      } else {
        await create(formData);
      }
      setOpen(false);
      mutate();
    } catch (error) {
      alert('Error al guardar');
    }
  };

  const handleChange = (e: any) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const pageCount = data?.count ? Math.ceil(data.count / 10) : 1; // Assuming page size is 10

  const TableSkeleton = () => (
    <Box sx={{ width: '100%' }}>
      <Table sx={{ minWidth: 650 }}>
        <TableHead>
          <TableRow>
            {columns.map((col) => (
              <TableCell key={col.key}><Skeleton variant="text" sx={{ fontSize: '1rem' }} /></TableCell>
            ))}
            <TableCell><Skeleton variant="text" sx={{ fontSize: '1rem' }} /></TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {Array.from(new Array(5)).map((_, index) => (
            <TableRow key={index}>
              {columns.map((col) => (
                <TableCell key={col.key}><Skeleton variant="text" /></TableCell>
              ))}
              <TableCell><Skeleton variant="text" /></TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Box>
  );

  return (
    <Paper sx={{ p: 2 }}>
      <Grid container justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
        <Grid item>
          {title && <h1 className="text-3xl font-bold">{title}</h1>}
        </Grid>
        <Grid item>
          <Button variant="contained" onClick={handleAdd}>
            Añadir
          </Button>
        </Grid>
      </Grid>
      
      <Box sx={{ mb: 2 }}>
        <TextField 
          fullWidth
          variant="outlined"
          label={`Buscar en ${title}`}
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
        />
      </Box>

      {isLoading && <TableSkeleton />}
      {error && <Alert severity="error">Error: {error.message}</Alert>}
      
      {!isLoading && !error && (
        <>
          <Box sx={{ overflowX: 'auto', width: '100%' }}>
            <Table sx={{ minWidth: 650 }}>
              <TableHead>
                <TableRow>
                  {columns.map((col) => (
                    <TableCell key={col.key} sx={{ whiteSpace: 'nowrap', minWidth: 120 }}>{col.label}</TableCell>
                  ))}
                  <TableCell sx={{ whiteSpace: 'nowrap', minWidth: 150 }}>Acciones</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {data?.results?.map((item: any, index: number) => (
                  <TableRow key={item.id || index}>
                    {columns.map((col) => (
                      <TableCell key={col.key} sx={{ whiteSpace: 'nowrap' }}>
                        {col.render ? col.render(item[col.key], item) : item[col.key]}
                      </TableCell>
                    ))}
                    <TableCell sx={{ whiteSpace: 'nowrap' }}>
                      <Button size="small" onClick={() => handleEdit(item)}>
                        Editar
                      </Button>
                      <Button size="small" color="error" onClick={() => handleDelete(item)}>
                        Eliminar
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Box>

          <Box sx={{ display: 'flex', justifyContent: 'center', mt: 2 }}>
            <Pagination 
              count={pageCount}
              page={page}
              onChange={(event, value) => setPage(value)}
              color="primary"
            />
          </Box>
        </>
      )}

      <Dialog open={open} onClose={() => setOpen(false)}>
        <DialogTitle>{editingItem ? 'Editar' : 'Añadir'} {title}</DialogTitle>
        <DialogContent>
          {fields.map((field) => (
            <div key={field.name} className="mb-4 pt-2">
              {field.type === 'select' ? (
                <FormControl fullWidth>
                  <InputLabel>{field.label}</InputLabel>
                  <Select
                    name={field.name}
                    value={formData[field.name] || ''}
                    onChange={handleChange}
                    required={field.required}
                  >
                    {field.options?.map((option) => (
                      <MenuItem key={String(option.value)} value={option.value}>
                        {option.label}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              ) : (
                <TextField
                  fullWidth
                  name={field.name}
                  label={field.label}
                  type={field.type}
                  value={formData[field.name] || ''}
                  onChange={handleChange}
                  required={field.required}
                />
              )}
            </div>
          ))}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpen(false)}>Cancelar</Button>
          <Button onClick={handleSave} disabled={isCreating || isUpdating}>
            Guardar
          </Button>
        </DialogActions>
      </Dialog>
    </Paper>
  );
};

export const ApiTable = React.memo(ApiTableComponent);