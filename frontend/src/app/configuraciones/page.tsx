'use client';

import React, { useState, useMemo } from 'react';
import { Box, Tabs, Tab } from '@mui/material';
import { ApiTable } from '@/components/ApiTable';
import { useApi } from '@/hooks/useApi';
import { Paginated } from '@/types/api';
import PerfilAgencia from '@/components/configuraciones/PerfilAgencia';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`configuraciones-tabpanel-${index}`}
      aria-labelledby={`configuraciones-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

function a11yProps(index: number) {
  return {
    id: `configuraciones-tab-${index}`,
    'aria-controls': `configuraciones-tabpanel-${index}`,
  };
}

export default function ConfiguracionesPage() {
  const [value, setValue] = useState(0);
  const { data: paises } = useApi<Paginated<any>>('/api/paises/');
  const { data: ciudades } = useApi<Paginated<any>>('/api/ciudades/');
  const { data: monedas } = useApi<Paginated<any>>('/api/monedas/');
  const { data: tiposCambio } = useApi<Paginated<any>>('/api/tipos-cambio/');
  const { data: aerolineas } = useApi<Paginated<any>>('/api/aerolineas/');

  const handleChange = (event: React.SyntheticEvent, newValue: number) => {
    setValue(newValue);
  };

  const paisesOptions = useMemo(() => (paises?.results || []).map((p: any) => ({ value: p.id, label: p.nombre })), [paises]);
  const ciudadesOptions = useMemo(() => (ciudades?.results || []).map((c: any) => ({ value: c.id, label: c.nombre })), [ciudades]);
  const monedasOptions = useMemo(() => {
    const monedasArray = Array.isArray(monedas) ? monedas : (monedas?.results || []);
    return monedasArray.map((m: any) => ({ value: m.id_moneda, label: m.nombre }));
  }, [monedas]);
  const tiposCambioOptions = useMemo(() => (tiposCambio?.results || []).map((t: any) => ({ value: t.id, label: `${t.moneda_origen_detalle.nombre} to ${t.moneda_destino_detalle.nombre}` })), [tiposCambio]);

  return (
    <Box sx={{ width: '100%' }}>
      <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tabs value={value} onChange={handleChange} aria-label="configuraciones tabs">
          <Tab label="Agencia" {...a11yProps(0)} />
          <Tab label="Países" {...a11yProps(1)} />
          <Tab label="Ciudades" {...a11yProps(2)} />
          <Tab label="Monedas" {...a11yProps(3)} />
          <Tab label="Tipos de Cambio" {...a11yProps(4)} />
          <Tab label="Aerolíneas" {...a11yProps(5)} />
        </Tabs>
      </Box>
      <TabPanel value={value} index={0}>
        <PerfilAgencia />
      </TabPanel>
      <TabPanel value={value} index={1}>
        <ApiTable
          endpoint="/api/paises/"
          columns={[
            { key: 'codigo_iso_2', label: 'Código ISO 2' },
            { key: 'codigo_iso_3', label: 'Código ISO 3' },
            { key: 'nombre', label: 'Nombre' },
          ]}
          title="Países"
          fields={[
            { name: 'codigo_iso_2', label: 'Código ISO 2', type: 'text', required: true },
            { name: 'codigo_iso_3', label: 'Código ISO 3', type: 'text', required: true },
            { name: 'nombre', label: 'Nombre', type: 'text', required: true },
          ]}
        />
      </TabPanel>
      <TabPanel value={value} index={2}>
        <ApiTable
          endpoint="/api/ciudades/"
          columns={[
            { key: 'nombre', label: 'Nombre' },
            { key: 'pais_detalle.nombre', label: 'País' },
            { key: 'region_estado', label: 'Región/Estado' },
          ]}
          title="Ciudades"
          fields={[
            { name: 'nombre', label: 'Nombre', type: 'text', required: true },
            { name: 'pais', label: 'País', type: 'select', options: paisesOptions, required: true },
            { name: 'region_estado', label: 'Región/Estado', type: 'text' },
          ]}
        />
      </TabPanel>
      <TabPanel value={value} index={3}>
        <ApiTable
          endpoint="/api/monedas/"
          columns={[
            { key: 'codigo_iso', label: 'Código ISO' },
            { key: 'nombre', label: 'Nombre' },
            { key: 'simbolo', label: 'Símbolo' },
            { key: 'es_moneda_local', label: 'Moneda Local' },
          ]}
          title="Monedas"
          fields={[
            { name: 'codigo_iso', label: 'Código ISO', type: 'text', required: true },
            { name: 'nombre', label: 'Nombre', type: 'text', required: true },
            { name: 'simbolo', label: 'Símbolo', type: 'text', required: true },
            { name: 'es_moneda_local', label: 'Moneda Local', type: 'select', options: [
              { value: true, label: 'Sí' },
              { value: false, label: 'No' }
            ], required: true },
          ]}
        />
      </TabPanel>
      <TabPanel value={value} index={4}>
        <ApiTable
          endpoint="/api/tipos-cambio/"
          columns={[
            { key: 'moneda_origen_detalle.nombre', label: 'Moneda Origen' },
            { key: 'moneda_destino_detalle.nombre', label: 'Moneda Destino' },
            { key: 'fecha_efectiva', label: 'Fecha Efectiva' },
            { key: 'tasa_conversion', label: 'Tasa de Conversión' },
          ]}
          title="Tipos de Cambio"
          fields={[
            { name: 'moneda_origen', label: 'Moneda Origen', type: 'select', options: monedasOptions, required: true },
            { name: 'moneda_destino', label: 'Moneda Destino', type: 'select', options: monedasOptions, required: true },
            { name: 'fecha_efectiva', label: 'Fecha Efectiva', type: 'text', required: true }, // Podría ser date, pero usar text por simplicidad
            { name: 'tasa_conversion', label: 'Tasa de Conversión', type: 'number', required: true },
          ]}
        />
      </TabPanel>
      <TabPanel value={value} index={5}>
        <ApiTable
          endpoint="/api/aerolineas/"
          columns={[
            { key: 'codigo_iata', label: 'Código IATA' },
            { key: 'nombre', label: 'Nombre' },
            { key: 'activa', label: 'Activa' },
          ]}
          title="Aerolíneas"
          fields={[
            { name: 'codigo_iata', label: 'Código IATA', type: 'text', required: true },
            { name: 'nombre', label: 'Nombre', type: 'text', required: true },
            { name: 'activa', label: 'Activa', type: 'select', options: [
              { value: true, label: 'Sí' },
              { value: false, label: 'No' }
            ], required: true },
          ]}
        />
      </TabPanel>
    </Box>
  );
}