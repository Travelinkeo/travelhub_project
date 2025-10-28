'use client';

import { useState } from 'react';
import {
  Box, Card, CardContent, Typography, Button, Table, TableBody, TableCell,
  TableContainer, TableHead, TableRow, Chip, IconButton, Dialog, DialogTitle,
  DialogContent, DialogActions, TextField, MenuItem, Alert
} from '@mui/material';
import { Add, Edit, Delete, PersonAdd } from '@mui/icons-material';
import { useApi } from '@/hooks/useApi';
import api from '@/lib/api';

interface Usuario {
  id: number;
  usuario_detalle: {
    id: number;
    username: string;
    email: string;
    first_name: string;
    last_name: string;
    nombre_completo: string;
  };
  agencia_nombre: string;
  rol: string;
  rol_display: string;
  activo: boolean;
}

const ROLES = [
  { value: 'admin', label: 'Administrador' },
  { value: 'gerente', label: 'Gerente' },
  { value: 'vendedor', label: 'Vendedor' },
  { value: 'contador', label: 'Contador' },
  { value: 'operador', label: 'Operador' },
  { value: 'consulta', label: 'Solo Consulta' },
];

export default function GestorUsuarios() {
  const { data: usuarios, isLoading, mutate } = useApi<Usuario[]>('/api/usuarios-agencia/');
  const [openDialog, setOpenDialog] = useState(false);
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    first_name: '',
    last_name: '',
    rol: 'vendedor'
  });
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const handleCreate = async () => {
    setSaving(true);
    setError(null);

    try {
      // Obtener primera agencia del usuario
      const agenciasRes = await api.get('/api/agencias/');
      const agencias = agenciasRes.data;
      
      if (!agencias || agencias.length === 0) {
        setError('No hay agencia configurada');
        return;
      }

      await api.post(`/api/agencias/${agencias[0].id}/agregar_usuario/`, formData);
      
      setOpenDialog(false);
      setFormData({
        username: '',
        email: '',
        password: '',
        first_name: '',
        last_name: '',
        rol: 'vendedor'
      });
      mutate();
    } catch (err: any) {
      setError(err.response?.data?.username?.[0] || err.response?.data?.email?.[0] || 'Error al crear usuario');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('¿Estás seguro de eliminar este usuario?')) return;

    try {
      await api.delete(`/api/usuarios-agencia/${id}/`);
      mutate();
    } catch (err) {
      alert('Error al eliminar usuario');
    }
  };

  const getRolColor = (rol: string) => {
    const colors: Record<string, 'error' | 'warning' | 'success' | 'info' | 'default'> = {
      admin: 'error',
      gerente: 'warning',
      vendedor: 'success',
      contador: 'info',
      operador: 'default',
      consulta: 'default'
    };
    return colors[rol] || 'default';
  };

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h6">Usuarios de la Agencia</Typography>
        <Button
          variant="contained"
          startIcon={<PersonAdd />}
          onClick={() => setOpenDialog(true)}
        >
          Agregar Usuario
        </Button>
      </Box>

      <Card>
        <CardContent>
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Usuario</TableCell>
                  <TableCell>Nombre</TableCell>
                  <TableCell>Email</TableCell>
                  <TableCell>Rol</TableCell>
                  <TableCell>Estado</TableCell>
                  <TableCell align="right">Acciones</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {usuarios?.map((usuario) => (
                  <TableRow key={usuario.id}>
                    <TableCell>{usuario.usuario_detalle.username}</TableCell>
                    <TableCell>{usuario.usuario_detalle.nombre_completo || '-'}</TableCell>
                    <TableCell>{usuario.usuario_detalle.email}</TableCell>
                    <TableCell>
                      <Chip
                        label={usuario.rol_display}
                        color={getRolColor(usuario.rol)}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={usuario.activo ? 'Activo' : 'Inactivo'}
                        color={usuario.activo ? 'success' : 'default'}
                        size="small"
                      />
                    </TableCell>
                    <TableCell align="right">
                      <IconButton size="small" color="error" onClick={() => handleDelete(usuario.id)}>
                        <Delete />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>

      {/* Dialog Crear Usuario */}
      <Dialog open={openDialog} onClose={() => setOpenDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Agregar Nuevo Usuario</DialogTitle>
        <DialogContent>
          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}

          <TextField
            label="Nombre de Usuario"
            value={formData.username}
            onChange={(e) => setFormData({ ...formData, username: e.target.value })}
            fullWidth
            margin="normal"
            required
          />

          <TextField
            label="Email"
            type="email"
            value={formData.email}
            onChange={(e) => setFormData({ ...formData, email: e.target.value })}
            fullWidth
            margin="normal"
            required
          />

          <TextField
            label="Contraseña"
            type="password"
            value={formData.password}
            onChange={(e) => setFormData({ ...formData, password: e.target.value })}
            fullWidth
            margin="normal"
            required
            helperText="Mínimo 8 caracteres"
          />

          <TextField
            label="Nombre"
            value={formData.first_name}
            onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
            fullWidth
            margin="normal"
          />

          <TextField
            label="Apellido"
            value={formData.last_name}
            onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
            fullWidth
            margin="normal"
          />

          <TextField
            label="Rol"
            select
            value={formData.rol}
            onChange={(e) => setFormData({ ...formData, rol: e.target.value })}
            fullWidth
            margin="normal"
            required
          >
            {ROLES.map((rol) => (
              <MenuItem key={rol.value} value={rol.value}>
                {rol.label}
              </MenuItem>
            ))}
          </TextField>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenDialog(false)}>Cancelar</Button>
          <Button onClick={handleCreate} variant="contained" disabled={saving}>
            {saving ? 'Creando...' : 'Crear Usuario'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
