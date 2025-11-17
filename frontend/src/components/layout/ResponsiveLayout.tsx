'use client';

import React, { useState } from 'react';
import { Box } from '@mui/material';
import Sidebar from './Sidebar';
import Header from './Header';
import BottomNav from './BottomNav'; // Import the new component

import { useTheme } from '@/contexts/ThemeContext';

export default function ResponsiveLayout({ children }: { children: React.ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { isDarkMode } = useTheme();

  const toggleSidebar = () => {
    setSidebarOpen(!sidebarOpen);
  };

  return (
    <Box sx={{ 
      display: 'flex', 
      height: '100vh', 
      bgcolor: 'background.default',
      color: 'text.primary'
    }}>
      {/* Sidebar is now hidden on mobile */}
      <Box sx={{ display: { xs: 'none', lg: 'block' } }}>
        <Sidebar isOpen={sidebarOpen} onToggle={toggleSidebar} />
      </Box>
      
      <Box sx={{ 
        flex: 1, 
        display: 'flex', 
        flexDirection: 'column', 
        minWidth: 0,
        bgcolor: 'background.default'
      }}>
        <Header onMenuToggle={toggleSidebar} />
        
        <Box component="main" sx={{ 
          flex: 1, 
          p: { xs: 2, lg: 3 }, 
          overflow: 'auto',
          bgcolor: 'background.default',
          color: 'text.primary',
          pb: { xs: '70px', lg: 3 } // Add padding-bottom for mobile to avoid overlap with BottomNav
        }}>
          {children}
        </Box>
        
        {/* Footer is now hidden on mobile */}
        <Box component="footer" sx={{
          p: 2,
          textAlign: 'center',
          borderTop: 1,
          borderColor: 'divider',
          bgcolor: 'background.paper',
          color: 'text.secondary',
          display: { xs: 'none', lg: 'block' } // Hide on mobile
        }}>
          <Box sx={{ 
            display: 'flex', 
            flexDirection: { xs: 'column', sm: 'row' },
            alignItems: 'center',
            justifyContent: 'center',
            gap: { xs: 1, sm: 2 }
          }}>
            <img src="/Linkeo Tech Logo.svg" alt="Linkeo Tech" style={{ height: '24px', width: 'auto' }} />
            <Box component="span" sx={{ fontSize: { xs: '0.75rem', sm: '0.875rem' } }}>
              © {new Date().getFullYear()} Linkeo Tech. Todos los derechos reservados.
            </Box>
          </Box>
        </Box>
      </Box>
      
      {/* Render BottomNav for mobile */}
      <BottomNav />
    </Box>
  );
}