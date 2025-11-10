'use client';

import React, { useState } from 'react';
import { Modal, Box, Typography, Button, CircularProgress, Alert } from '@mui/material';

const style = {
  position: 'absolute' as 'absolute',
  top: '50%',
  left: '50%',
  transform: 'translate(-50%, -50%)',
  width: 400,
  bgcolor: 'background.paper',
  border: '2px solid #000',
  boxShadow: 24,
  p: 4,
};

interface BoletoImportModalProps {
  open: boolean;
  onClose: () => void;
  onUploadComplete: () => void;
}

export default function BoletoImportModal({ open, onClose, onUploadComplete }: BoletoImportModalProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files) {
      setSelectedFile(event.target.files[0]);
      setError(null);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setError('Por favor, seleccione un archivo.');
      return;
    }

    setIsUploading(true);
    setError(null);

    const formData = new FormData();
    formData.append('archivo_boleto', selectedFile, selectedFile.name); // Incluir nombre explícitamente

    const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || process.env.NEXT_PUBLIC_API_BASE_URL || '';
    const endpoint = `${apiBaseUrl}/api/boletos-importados/`;
    
    // Obtener token de autenticación
    const token = localStorage.getItem('accessToken'); // JWT token
    const headers: HeadersInit = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers,
        body: formData,
      });

      if (!response.ok) {
        const text = await response.text();
        console.error('Error response:', text);
        try {
          const errorData = JSON.parse(text);
          throw new Error(errorData.detail || 'Error al subir el archivo.');
        } catch {
          throw new Error(`Error ${response.status}: ${text.substring(0, 200)}`);
        }
      }

      // Success
      onUploadComplete();
      handleClose();

    } catch (e) {
      const errorMessage = e instanceof Error ? e.message : 'Ocurrió un error desconocido.';
      console.error('Upload error:', e);
      setError(errorMessage);
    } finally {
      setIsUploading(false);
    }
  };

  const handleClose = () => {
    setSelectedFile(null);
    setError(null);
    onClose();
  };

  return (
    <Modal open={open} onClose={handleClose}>
      <Box sx={style}>
        <Typography variant="h6" component="h2" gutterBottom>
          Importar Nuevo Boleto
        </Typography>
        
        <Button variant="contained" component="label" fullWidth>
          Seleccionar Archivo
          <input type="file" hidden onChange={handleFileChange} accept=".pdf,.txt,.eml" />
        </Button>

        {selectedFile && <Typography sx={{ mt: 2 }}>Archivo: {selectedFile.name}</Typography>}
        {error && <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>}

        <Box sx={{ mt: 3, display: 'flex', justifyContent: 'flex-end', alignItems: 'center' }}>
          {isUploading && <CircularProgress size={24} sx={{ mr: 2 }} />}
          <Button onClick={handleClose} sx={{ mr: 1 }} disabled={isUploading}>Cancelar</Button>
          <Button onClick={handleUpload} variant="contained" disabled={!selectedFile || isUploading}>
            Subir
          </Button>
        </Box>
      </Box>
    </Modal>
  );
}
