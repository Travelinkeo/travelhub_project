'use client';

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { IconButton, Typography, Box, Button, Tooltip } from '@mui/material';
import { Menu, Settings, DarkMode, LightMode, Logout } from '@mui/icons-material';
import { useTheme } from '@/contexts/ThemeContext';
import { useAuth } from '@/contexts/AuthContext';

interface Tasa {
  valor: number;
  fecha: string;
  nombre: string;
}

interface Tasas {
  oficial?: Tasa;
  paralelo?: Tasa;
}

interface HeaderProps {
  onMenuToggle: () => void;
}

const Header = ({ onMenuToggle }: HeaderProps) => {
  const router = useRouter();
  const { isDarkMode, toggleTheme } = useTheme();
  const { user, logout } = useAuth();
  const [tasas, setTasas] = useState<Tasas | null>(null);

  useEffect(() => {
    const fetchTasas = async () => {
      try {
        const response = await fetch('http://127.0.0.1:8000/api/contabilidad/api/tasas/actuales/');
        const data = await response.json();
        setTasas(data);
      } catch (error) {
        console.error('Error obteniendo tasas:', error);
      }
    };

    fetchTasas();
    const interval = setInterval(fetchTasas, 300000); // 5 minutos
    return () => clearInterval(interval);
  }, []);

  const handleSettingsClick = () => {
    router.push('/configuraciones');
  };

  return (
    <Box component="header" sx={{
      boxShadow: 1,
      p: 2,
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      bgcolor: 'background.paper',
      color: 'text.primary',
      borderBottom: 1,
      borderColor: 'divider'
    }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
        <IconButton 
          onClick={onMenuToggle}
          sx={{ 
            display: { lg: 'none' }, 
            mr: 2,
            color: 'text.primary'
          }}
          size="medium"
        >
          <Menu fontSize="medium" />
        </IconButton>
        
        {/* Tasas de Cambio */}
        {tasas && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
            {/* BCV Oficial */}
            {tasas.oficial && (
              <Tooltip title="BCV Oficial" arrow>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                  <Typography variant="body2" color="text.secondary" sx={{ fontSize: '0.875rem' }}>
                    Oficial:
                  </Typography>
                  <Typography variant="body2" fontWeight="bold" color="success.main" sx={{ fontSize: '0.875rem' }}>
                    {tasas.oficial.valor.toFixed(2)}
                  </Typography>
                  <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.75rem' }}>
                    Bs
                  </Typography>
                </Box>
              </Tooltip>
            )}
            
            {/* Separador */}
            {tasas.oficial && tasas.paralelo && (
              <Typography color="text.disabled">|</Typography>
            )}
            
            {/* Dólar No Oficial */}
            {tasas.paralelo && (
              <Tooltip title="Mercado Paralelo" arrow>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                  <Typography variant="body2" color="text.secondary" sx={{ fontSize: '0.875rem' }}>
                    No Oficial:
                  </Typography>
                  <Typography variant="body2" fontWeight="bold" color="primary.main" sx={{ fontSize: '0.875rem' }}>
                    {tasas.paralelo.valor.toFixed(2)}
                  </Typography>
                  <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.75rem' }}>
                    Bs
                  </Typography>
                </Box>
              </Tooltip>
            )}
            
            {/* Separador */}
            <Typography color="text.disabled">|</Typography>
          </Box>
        )}
        
        <Typography variant="h6" component="div" color="text.primary">
          Dashboard
        </Typography>
      </Box>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <Typography 
          variant="body2" 
          sx={{ display: { xs: 'none', sm: 'block' } }} 
          color="text.secondary"
        >
          Bienvenido, {user?.username || 'Usuario'}
        </Typography>
        <IconButton 
          onClick={toggleTheme}
          color="inherit"
          aria-label="Cambiar tema"
        >
          {isDarkMode ? <LightMode /> : <DarkMode />}
        </IconButton>
        <IconButton color="primary" onClick={handleSettingsClick} aria-label="Configuraciones">
          <Settings />
        </IconButton>
        <IconButton 
          color="error" 
          onClick={logout}
          aria-label="Cerrar sesión"
          title="Cerrar sesión"
        >
          <Logout />
        </IconButton>
      </Box>
    </Box>
  );
};

export default Header;