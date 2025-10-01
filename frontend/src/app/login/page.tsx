
'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { Box, Button, TextField, Typography, Paper, Alert } from '@mui/material';
import { apiMutate } from '@/lib/api';

export default function LoginPage() {
  const router = useRouter();
  const { register, handleSubmit } = useForm();
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async (data: any) => {
    try {
      setError(null);
      const response = await apiMutate('/api/auth/login/', {
        method: 'POST',
        body: data,
      });
      if (response.token) {
        localStorage.setItem('auth_token', response.token);
        router.push('/'); // Redirect to home page after login
      } else {
        setError('No se recibió un token.');
      }
    } catch (err: any) {
      setError(err.message || 'Error al iniciar sesión.');
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
            <Button type="submit" variant="contained" fullWidth>
              Entrar
            </Button>
          </Box>
        </form>
      </Paper>
    </Box>
  );
}
