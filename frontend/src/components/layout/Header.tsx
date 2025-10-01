'use client';

import React from 'react';
import { useRouter } from 'next/navigation';
import { IconButton, Typography, Box } from '@mui/material';
import { Menu, Settings, DarkMode, LightMode } from '@mui/icons-material';
import { useTheme } from '@/contexts/ThemeContext';

interface HeaderProps {
  onMenuToggle: () => void;
}

const Header = ({ onMenuToggle }: HeaderProps) => {
  const router = useRouter();
  const { isDarkMode, toggleTheme } = useTheme();

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
      <Box sx={{ display: 'flex', alignItems: 'center' }}>
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
          Bienvenido, Usuario
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
      </Box>
    </Box>
  );
};

export default Header;