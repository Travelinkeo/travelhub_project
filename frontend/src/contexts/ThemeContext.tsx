'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';
import { createTheme, ThemeProvider } from '@mui/material/styles';
import { CssBaseline } from '@mui/material';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDayjs } from '@mui/x-date-pickers/AdapterDayjs';

interface ThemeContextType {
  isDarkMode: boolean;
  toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeContextProvider');
  }
  return context;
};

export const ThemeContextProvider = ({ children }: { children: React.ReactNode }) => {
  const [isDarkMode, setIsDarkMode] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    const saved = localStorage.getItem('darkMode');
    if (saved) {
      setIsDarkMode(JSON.parse(saved));
    }
  }, []);

  const toggleTheme = () => {
    console.log('Toggle theme clicked, current mode:', isDarkMode);
    const newMode = !isDarkMode;
    setIsDarkMode(newMode);
    if (mounted) {
      localStorage.setItem('darkMode', JSON.stringify(newMode));
    }
    console.log('New mode set to:', newMode);
  };

  const theme = React.useMemo(() => createTheme({
    palette: {
      mode: isDarkMode ? 'dark' : 'light',
      primary: {
        main: '#1976d2',
      },
      secondary: {
        main: '#dc004e',
      },
      background: {
        default: isDarkMode ? '#121212' : '#ffffff',
        paper: isDarkMode ? '#1e1e1e' : '#ffffff',
      },
      text: {
        primary: isDarkMode ? '#ffffff' : '#000000',
        secondary: isDarkMode ? '#b3b3b3' : '#666666',
      },
    },
  }), [isDarkMode]);

  if (!mounted) {
    return (
      <ThemeContext.Provider value={{ isDarkMode: false, toggleTheme: () => {} }}>
        <LocalizationProvider dateAdapter={AdapterDayjs}>
          <ThemeProvider theme={createTheme({ palette: { mode: 'light' } })}>
            <CssBaseline />
            {children}
          </ThemeProvider>
        </LocalizationProvider>
      </ThemeContext.Provider>
    );
  }

  return (
    <ThemeContext.Provider value={{ isDarkMode, toggleTheme }}>
      <LocalizationProvider dateAdapter={AdapterDayjs}>
        <ThemeProvider theme={theme}>
          <CssBaseline />
          {children}
        </ThemeProvider>
      </LocalizationProvider>
    </ThemeContext.Provider>
  );
};