
'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { Box, Button, TextField, Typography, Paper, Alert } from '@mui/material';
import { useAuth } from '@/contexts/AuthContext';

export default function LoginPage() {
  const { login } = useAuth();
  const { register, handleSubmit } = useForm();
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const onSubmit = async (data: any) => {
    try {
      setError(null);
      setIsLoading(true);
      await login(data.username, data.password);
    } catch (err: any) {
      setError(err.message || 'Error al iniciar sesión.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Box sx={{ maxWidth: 400, mx: 'auto', mt: 8 }}>
      <Paper elevation={3} sx={{ p: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Iniciar Sesión
        </Typography>
        {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
        <form onSubmit={handleSubmit(onSubmit)}>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <TextField
              label="Usuario"
              {...register('username', { required: true })}
              fullWidth
            />
            <TextField
              label="Contraseña"
              type="password"
              {...register('password', { required: true })}
              fullWidth
            />
            <Button type="submit" variant="contained" fullWidth disabled={isLoading}>
              {isLoading ? 'Iniciando sesión...' : 'Entrar'}
            </Button>
          </Box>
        </form>
      </Paper>
    </Box>
  );
}
