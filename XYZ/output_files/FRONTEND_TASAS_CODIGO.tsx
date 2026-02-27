// Componente Header con Tasas de Cambio
// Ubicación sugerida: frontend/src/components/Layout/Header.tsx

import { useEffect, useState } from 'react';

interface Tasa {
  valor: number;
  fecha: string;
  nombre: string;
}

interface Tasas {
  oficial?: Tasa;
  paralelo?: Tasa;
}

export default function Header() {
  const [tasas, setTasas] = useState<Tasas | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchTasas = async () => {
      try {
        const response = await fetch('http://127.0.0.1:8000/api/contabilidad/api/tasas/actuales/');
        const data = await response.json();
        setTasas(data);
      } catch (error) {
        console.error('Error obteniendo tasas:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchTasas();
    
    // Actualizar cada 5 minutos
    const interval = setInterval(fetchTasas, 300000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="flex justify-between items-center px-6 py-3 bg-white shadow-sm">
      {/* Lado izquierdo - Tasas + Bienvenida */}
      <div className="flex items-center gap-3">
        {loading ? (
          <div className="text-sm text-gray-400">Cargando tasas...</div>
        ) : tasas ? (
          <>
            {/* BCV Oficial */}
            {tasas.oficial && (
              <div className="flex items-center gap-1 text-sm">
                <span className="text-gray-600">Oficial:</span>
                <span className="font-semibold text-green-600">
                  {tasas.oficial.valor.toFixed(2)}
                </span>
                <span className="text-gray-500 text-xs">Bs</span>
              </div>
            )}
            
            {/* Separador */}
            {tasas.oficial && tasas.paralelo && (
              <div className="text-gray-300">|</div>
            )}
            
            {/* Dólar No Oficial */}
            {tasas.paralelo && (
              <div className="flex items-center gap-1 text-sm">
                <span className="text-gray-600">No Oficial:</span>
                <span className="font-semibold text-blue-600">
                  {tasas.paralelo.valor.toFixed(2)}
                </span>
                <span className="text-gray-500 text-xs">Bs</span>
              </div>
            )}
          </>
        ) : null}
        
        {/* Separador */}
        <div className="text-gray-300">|</div>
        
        {/* Bienvenida */}
        <div className="text-sm text-gray-700">
          Bienvenido, <span className="font-medium">Armando3105</span>
        </div>
      </div>

      {/* Lado derecho - Menú usuario */}
      <div className="flex items-center gap-4">
        {/* Tu menú actual aquí */}
        <button className="text-gray-600 hover:text-gray-900">
          Menú
        </button>
      </div>
    </header>
  );
}

// ============================================
// Versión Alternativa: Con Tooltip
// ============================================

export function HeaderConTooltip() {
  const [tasas, setTasas] = useState<Tasas | null>(null);
  const [showTooltip, setShowTooltip] = useState(false);

  useEffect(() => {
    const fetchTasas = async () => {
      try {
        const response = await fetch('http://127.0.0.1:8000/api/contabilidad/api/tasas/actuales/');
        const data = await response.json();
        setTasas(data);
      } catch (error) {
        console.error('Error:', error);
      }
    };

    fetchTasas();
    const interval = setInterval(fetchTasas, 300000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="flex justify-between items-center px-6 py-3 bg-white shadow-sm">
      <div className="flex items-center gap-3">
        {/* Tasas con Tooltip */}
        {tasas && (
          <div 
            className="relative"
            onMouseEnter={() => setShowTooltip(true)}
            onMouseLeave={() => setShowTooltip(false)}
          >
            <div className="flex items-center gap-2 text-sm cursor-pointer">
              <span className="text-gray-600">USD:</span>
              <span className="font-semibold text-green-600">
                {tasas.oficial?.valor.toFixed(2)}
              </span>
              <span className="text-gray-400 text-xs">▼</span>
            </div>
            
            {/* Tooltip */}
            {showTooltip && (
              <div className="absolute top-full left-0 mt-2 bg-white shadow-lg rounded-lg p-3 z-50 min-w-[200px]">
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">Oficial:</span>
                    <span className="font-semibold text-green-600">
                      {tasas.oficial?.valor.toFixed(2)} Bs
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">No Oficial:</span>
                    <span className="font-semibold text-blue-600">
                      {tasas.paralelo?.valor.toFixed(2)} Bs
                    </span>
                  </div>
                  <div className="text-xs text-gray-400 pt-2 border-t">
                    Actualizado: {new Date(tasas.oficial?.fecha || '').toLocaleTimeString('es-VE', { hour: '2-digit', minute: '2-digit' })}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
        
        <div className="text-gray-300">|</div>
        
        <div className="text-sm text-gray-700">
          Bienvenido, <span className="font-medium">Armando3105</span>
        </div>
      </div>

      <div className="flex items-center gap-4">
        {/* Menú */}
      </div>
    </header>
  );
}

// ============================================
// Versión Material-UI (si usas MUI)
// ============================================

import { Box, Typography, Tooltip } from '@mui/material';

export function HeaderMUI() {
  const [tasas, setTasas] = useState<Tasas | null>(null);

  useEffect(() => {
    const fetchTasas = async () => {
      try {
        const response = await fetch('http://127.0.0.1:8000/api/contabilidad/api/tasas/actuales/');
        const data = await response.json();
        setTasas(data);
      } catch (error) {
        console.error('Error:', error);
      }
    };

    fetchTasas();
    const interval = setInterval(fetchTasas, 300000);
    return () => clearInterval(interval);
  }, []);

  return (
    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', px: 3, py: 1.5, bgcolor: 'white', boxShadow: 1 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
        {tasas && (
          <>
            <Tooltip title="BCV Oficial" arrow>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                <Typography variant="body2" color="text.secondary">Oficial:</Typography>
                <Typography variant="body2" fontWeight="bold" color="success.main">
                  {tasas.oficial?.valor.toFixed(2)}
                </Typography>
                <Typography variant="caption" color="text.secondary">Bs</Typography>
              </Box>
            </Tooltip>
            
            <Typography color="text.disabled">|</Typography>
            
            <Tooltip title="Mercado Paralelo" arrow>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                <Typography variant="body2" color="text.secondary">No Oficial:</Typography>
                <Typography variant="body2" fontWeight="bold" color="primary.main">
                  {tasas.paralelo?.valor.toFixed(2)}
                </Typography>
                <Typography variant="caption" color="text.secondary">Bs</Typography>
              </Box>
            </Tooltip>
          </>
        )}
        
        <Typography color="text.disabled">|</Typography>
        
        <Typography variant="body2" color="text.primary">
          Bienvenido, <Box component="span" fontWeight="medium">Armando3105</Box>
        </Typography>
      </Box>

      <Box>
        {/* Menú */}
      </Box>
    </Box>
  );
}
