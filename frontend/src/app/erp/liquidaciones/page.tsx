'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import { Button, TextField, Select, MenuItem, Chip, Dialog, DialogTitle, DialogContent, DialogActions } from '@mui/material';

interface Liquidacion {
  id_liquidacion: number;
  proveedor_detalle: { nombre_comercial: string };
  venta_detalle: string;
  fecha_emision: string;
  monto_total: number;
  saldo_pendiente: number;
  estado: string;
  estado_display: string;
}

export default function LiquidacionesPage() {
  const [liquidaciones, setLiquidaciones] = useState<Liquidacion[]>([]);
  const [filtroEstado, setFiltroEstado] = useState('');
  const [search, setSearch] = useState('');
  const [pagoDialog, setPagoDialog] = useState<{ open: boolean; liquidacion: Liquidacion | null; monto: string }>({ open: false, liquidacion: null, monto: '' });

  const cargarLiquidaciones = async () => {
    try {
      const params = new URLSearchParams();
      if (filtroEstado) params.append('estado', filtroEstado);
      if (search) params.append('search', search);
      
      const response = await api.get(`/api/liquidaciones/?${params}`);
      setLiquidaciones(response.data.results || response.data);
    } catch (error) {
      console.error('Error cargando liquidaciones:', error);
    }
  };

  useEffect(() => {
    cargarLiquidaciones();
  }, [filtroEstado, search]);

  const marcarPagada = async (id: number) => {
    try {
      await api.post(`/api/liquidaciones/${id}/marcar_pagada/`);
      alert('Liquidación marcada como pagada');
      cargarLiquidaciones();
    } catch (error) {
      console.error('Error:', error);
      alert('Error al marcar como pagada');
    }
  };

  const registrarPagoParcial = async () => {
    if (!pagoDialog.liquidacion) return;
    try {
      await api.post(`/api/liquidaciones/${pagoDialog.liquidacion.id_liquidacion}/registrar_pago_parcial/`, {
        monto: parseFloat(pagoDialog.monto)
      });
      alert('Pago parcial registrado');
      setPagoDialog({ open: false, liquidacion: null, monto: '' });
      cargarLiquidaciones();
    } catch (error) {
      console.error('Error:', error);
      alert('Error al registrar pago');
    }
  };

  return (
    <div className="p-6">
      <h1 className="text-3xl font-bold mb-6">Liquidaciones a Proveedores</h1>

      <div className="flex gap-4 mb-6">
        <TextField
          label="Buscar"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          size="small"
          className="flex-1"
        />
        <Select
          value={filtroEstado}
          onChange={(e) => setFiltroEstado(e.target.value)}
          displayEmpty
          size="small"
          className="w-48"
        >
          <MenuItem value="">Todos los estados</MenuItem>
          <MenuItem value="PEN">Pendiente</MenuItem>
          <MenuItem value="PAR">Parcial</MenuItem>
          <MenuItem value="PAG">Pagada</MenuItem>
        </Select>
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">ID</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Proveedor</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Venta</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Fecha</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Total</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Saldo</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Estado</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Acciones</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {liquidaciones.map((liq) => (
              <tr key={liq.id_liquidacion}>
                <td className="px-6 py-4 whitespace-nowrap text-sm">{liq.id_liquidacion}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm">{liq.proveedor_detalle?.nombre_comercial}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm">{liq.venta_detalle}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm">{new Date(liq.fecha_emision).toLocaleDateString()}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm">${liq.monto_total.toFixed(2)}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm">${liq.saldo_pendiente.toFixed(2)}</td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <Chip 
                    label={liq.estado_display} 
                    color={liq.estado === 'PAG' ? 'success' : liq.estado === 'PAR' ? 'warning' : 'error'}
                    size="small"
                  />
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm space-x-2">
                  {liq.estado !== 'PAG' && (
                    <>
                      <Button 
                        size="small" 
                        variant="contained" 
                        color="success"
                        onClick={() => marcarPagada(liq.id_liquidacion)}
                      >
                        Pagar Total
                      </Button>
                      <Button 
                        size="small" 
                        variant="outlined"
                        onClick={() => setPagoDialog({ open: true, liquidacion: liq, monto: '' })}
                      >
                        Pago Parcial
                      </Button>
                    </>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Dialog open={pagoDialog.open} onClose={() => setPagoDialog({ open: false, liquidacion: null, monto: '' })}>
        <DialogTitle>Registrar Pago Parcial</DialogTitle>
        <DialogContent>
          <TextField
            label="Monto a Pagar"
            type="number"
            value={pagoDialog.monto}
            onChange={(e) => setPagoDialog({ ...pagoDialog, monto: e.target.value })}
            fullWidth
            margin="normal"
          />
          {pagoDialog.liquidacion && (
            <p className="text-sm text-gray-600 mt-2">
              Saldo pendiente: ${pagoDialog.liquidacion.saldo_pendiente.toFixed(2)}
            </p>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPagoDialog({ open: false, liquidacion: null, monto: '' })}>Cancelar</Button>
          <Button onClick={registrarPagoParcial} variant="contained">Registrar</Button>
        </DialogActions>
      </Dialog>
    </div>
  );
}
