'use client';

import { useState, useEffect } from 'react';
import {
  Box, Card, CardContent, Grid, TextField, Button, Typography,
  Alert, CircularProgress, Avatar, IconButton
} from '@mui/material';
import { PhotoCamera, Save } from '@mui/icons-material';
import { useApi } from '@/hooks/useApi';
import api from '@/lib/api';

interface Agencia {
  id: number;
  nombre: string;
  nombre_comercial: string;
  rif: string;
  iata: string;
  telefono_principal: string;
  telefono_secundario: string;
  email_principal: string;
  email_soporte: string;
  email_ventas: string;
  direccion: string;
  ciudad: string;
  estado: string;
  pais: string;
  codigo_postal: string;
  logo: string | null;
  color_primario: string;
  color_secundario: string;
  website: string;
  facebook: string;
  instagram: string;
  twitter: string;
  whatsapp: string;
  moneda_principal: string;
  timezone: string;
  idioma: string;
}

export default function PerfilAgencia() {
  const { data: response, isLoading } = useApi<any>('/api/agencias/');
  const [agencia, setAgencia] = useState<Agencia | null>(null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  useEffect(() => {
    console.log('Response:', response);
    const agencias = Array.isArray(response) ? response : response?.results || [];
    if (agencias.length > 0) {
      setAgencia(agencias[0]);
    }
  }, [response]);

  const handleChange = (field: keyof Agencia, value: string) => {
    if (agencia) {
      setAgencia({ ...agencia, [field]: value });
    }
  };

  const handleSave = async () => {
    if (!agencia) return;
    
    setSaving(true);
    setMessage(null);
    
    try {
      await api.put(`/api/agencias/${agencia.id}/`, agencia);
      setMessage({ type: 'success', text: 'Perfil actualizado correctamente' });
    } catch (error) {
      setMessage({ type: 'error', text: 'Error al actualizar el perfil' });
    } finally {
      setSaving(false);
    }
  };

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" p={4}>
        <CircularProgress />
      </Box>
    );
  }

  if (!agencia) {
    return (
      <Alert severity="info">
        No hay agencia configurada. Contacta al administrador.
      </Alert>
    );
  }

  return (
    <Box>
      {message && (
        <Alert severity={message.type} sx={{ mb: 2 }} onClose={() => setMessage(null)}>
          {message.text}
        </Alert>
      )}

      <Grid container spacing={3}>
        {/* Logo y Branding */}
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Logo y Branding</Typography>
              
              <Box display="flex" flexDirection="column" alignItems="center" gap={2}>
                <Avatar
                  src={agencia.logo || undefined}
                  sx={{ width: 120, height: 120 }}
                  variant="rounded"
                >
                  {agencia.nombre[0]}
                </Avatar>
                
                <Button
                  variant="outlined"
                  startIcon={<PhotoCamera />}
                  component="label"
                  size="small"
                >
                  Cambiar Logo
                  <input type="file" hidden accept="image/*" />
                </Button>

                <TextField
                  label="Color Primario"
                  type="color"
                  value={agencia.color_primario}
                  onChange={(e) => handleChange('color_primario', e.target.value)}
                  fullWidth
                  size="small"
                />

                <TextField
                  label="Color Secundario"
                  type="color"
                  value={agencia.color_secundario}
                  onChange={(e) => handleChange('color_secundario', e.target.value)}
                  fullWidth
                  size="small"
                />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Información Básica */}
        <Grid item xs={12} md={8}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Información Básica</Typography>
              
              <Grid container spacing={2}>
                <Grid item xs={12} sm={6}>
                  <TextField
                    label="Nombre de la Agencia"
                    value={agencia.nombre}
                    onChange={(e) => handleChange('nombre', e.target.value)}
                    fullWidth
                    required
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    label="Nombre Comercial"
                    value={agencia.nombre_comercial}
                    onChange={(e) => handleChange('nombre_comercial', e.target.value)}
                    fullWidth
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    label="RIF"
                    value={agencia.rif}
                    onChange={(e) => handleChange('rif', e.target.value)}
                    fullWidth
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    label="Código IATA"
                    value={agencia.iata}
                    onChange={(e) => handleChange('iata', e.target.value)}
                    fullWidth
                  />
                </Grid>
              </Grid>
            </CardContent>
          </Card>

          {/* Contacto */}
          <Card sx={{ mt: 2 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>Contacto</Typography>
              
              <Grid container spacing={2}>
                <Grid item xs={12} sm={6}>
                  <TextField
                    label="Teléfono Principal"
                    value={agencia.telefono_principal}
                    onChange={(e) => handleChange('telefono_principal', e.target.value)}
                    fullWidth
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    label="Teléfono Secundario"
                    value={agencia.telefono_secundario}
                    onChange={(e) => handleChange('telefono_secundario', e.target.value)}
                    fullWidth
                  />
                </Grid>
                <Grid item xs={12} sm={4}>
                  <TextField
                    label="Email Principal"
                    type="email"
                    value={agencia.email_principal}
                    onChange={(e) => handleChange('email_principal', e.target.value)}
                    fullWidth
                    required
                  />
                </Grid>
                <Grid item xs={12} sm={4}>
                  <TextField
                    label="Email Soporte"
                    type="email"
                    value={agencia.email_soporte}
                    onChange={(e) => handleChange('email_soporte', e.target.value)}
                    fullWidth
                  />
                </Grid>
                <Grid item xs={12} sm={4}>
                  <TextField
                    label="Email Ventas"
                    type="email"
                    value={agencia.email_ventas}
                    onChange={(e) => handleChange('email_ventas', e.target.value)}
                    fullWidth
                  />
                </Grid>
                <Grid item xs={12}>
                  <TextField
                    label="WhatsApp"
                    value={agencia.whatsapp}
                    onChange={(e) => handleChange('whatsapp', e.target.value)}
                    fullWidth
                    placeholder="+58 412 1234567"
                  />
                </Grid>
              </Grid>
            </CardContent>
          </Card>

          {/* Dirección */}
          <Card sx={{ mt: 2 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>Dirección</Typography>
              
              <Grid container spacing={2}>
                <Grid item xs={12}>
                  <TextField
                    label="Dirección"
                    value={agencia.direccion}
                    onChange={(e) => handleChange('direccion', e.target.value)}
                    fullWidth
                    multiline
                    rows={2}
                  />
                </Grid>
                <Grid item xs={12} sm={4}>
                  <TextField
                    label="Ciudad"
                    value={agencia.ciudad}
                    onChange={(e) => handleChange('ciudad', e.target.value)}
                    fullWidth
                  />
                </Grid>
                <Grid item xs={12} sm={4}>
                  <TextField
                    label="Estado"
                    value={agencia.estado}
                    onChange={(e) => handleChange('estado', e.target.value)}
                    fullWidth
                  />
                </Grid>
                <Grid item xs={12} sm={4}>
                  <TextField
                    label="País"
                    value={agencia.pais}
                    onChange={(e) => handleChange('pais', e.target.value)}
                    fullWidth
                  />
                </Grid>
              </Grid>
            </CardContent>
          </Card>

          {/* Redes Sociales */}
          <Card sx={{ mt: 2 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>Redes Sociales</Typography>
              
              <Grid container spacing={2}>
                <Grid item xs={12} sm={6}>
                  <TextField
                    label="Website"
                    value={agencia.website}
                    onChange={(e) => handleChange('website', e.target.value)}
                    fullWidth
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    label="Facebook"
                    value={agencia.facebook}
                    onChange={(e) => handleChange('facebook', e.target.value)}
                    fullWidth
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    label="Instagram"
                    value={agencia.instagram}
                    onChange={(e) => handleChange('instagram', e.target.value)}
                    fullWidth
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    label="Twitter"
                    value={agencia.twitter}
                    onChange={(e) => handleChange('twitter', e.target.value)}
                    fullWidth
                  />
                </Grid>
              </Grid>
            </CardContent>
          </Card>

          <Box mt={3} display="flex" justifyContent="flex-end">
            <Button
              variant="contained"
              startIcon={<Save />}
              onClick={handleSave}
              disabled={saving}
            >
              {saving ? 'Guardando...' : 'Guardar Cambios'}
            </Button>
          </Box>
        </Grid>
      </Grid>
    </Box>
  );
}
