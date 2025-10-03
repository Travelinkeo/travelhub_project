'use client';

import React, { useState, useMemo, useEffect } from 'react';
import { useForm, useFieldArray, Controller, useWatch } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Button, TextField, Typography, Grid, Paper, IconButton, Autocomplete } from '@mui/material';
import AddCircleOutlineIcon from '@mui/icons-material/AddCircleOutline';
import DeleteIcon from '@mui/icons-material/Delete';
import EditIcon from '@mui/icons-material/Edit';
import { useApi } from '@/hooks/useApi';
import { apiMutate } from '@/lib/api';
import { Cliente, Moneda, ProductoServicio, Paginated } from '@/types/api';
import { useRouter } from 'next/navigation';
import { useDebounce } from '@/hooks/useDebounce';
import AlojamientoForm from './AlojamientoForm';
import AlquilerAutoForm from './AlquilerAutoForm';
import TrasladoForm from './TrasladoForm';
import TourActividadForm from './TourActividadForm';
import SeguroViajeForm from './SeguroViajeForm';
import ServicioAdicionalForm from './ServicioAdicionalForm';

// --- Zod Schemas ---
const alojamientoSchema = z.object({
   nombre_establecimiento: z.string().min(1, 'El nombre es requerido'),
   ciudad: z.number().min(1, "La ciudad es requerida"),
   check_in: z.string().nullable().optional(),
   check_out: z.string().nullable().optional(),
   regimen_alimentacion: z.string().optional(),
   habitaciones: z.number().min(1).default(1),
   proveedor: z.number().optional(),
   notas: z.string().optional(),
 }).optional().nullable();

const alquilerAutoSchema = z.object({
  compania_rentadora: z.string().optional(),
  categoria_auto: z.string().optional(),
  fecha_recogida: z.string().nullable().optional(),
  hora_recogida: z.string().nullable().optional(),
  fecha_devolucion: z.string().nullable().optional(),
  hora_devolucion: z.string().nullable().optional(),
  ciudad_retiro: z.number().optional(),
  ciudad_devolucion: z.number().optional(),
  incluye_seguro: z.boolean().optional(),
  numero_confirmacion: z.string().optional(),
  proveedor: z.number().optional(),
  notas: z.string().optional(),
}).optional().nullable();

const trasladoSchema = z.object({
  origen: z.string().optional(),
  destino: z.string().optional(),
  fecha_hora: z.string().nullable().optional(),
  hora: z.string().nullable().optional(),
  pasajeros: z.number().optional(),
  proveedor: z.number().optional(),
  notas: z.string().optional(),
}).optional().nullable();

const tourActividadSchema = z.object({
  nombre: z.string().optional(),
  fecha: z.string().nullable().optional(),
  duracion_horas: z.number().optional(),
  incluye: z.string().optional(),
  no_incluye: z.string().optional(),
  proveedor: z.number().optional(),
  notas: z.string().optional(),
}).optional().nullable();

const seguroViajeSchema = z.object({
  fecha_salida: z.string().nullable().optional(),
  fecha_regreso: z.string().nullable().optional(),
  plan: z.string().optional(),
  cobertura_monto: z.number().optional(),
  proveedor: z.number().optional(),
  notas: z.string().optional(),
}).optional().nullable();

const servicioAdicionalSchema = z.object({
  tipo_servicio: z.string().optional(),
  descripcion: z.string().optional(),
  lugar: z.string().optional(),
  fecha: z.string().nullable().optional(),
  hora: z.string().nullable().optional(),
  duracion_horas: z.number().optional(),
  pasajeros: z.number().optional(),
  destino: z.string().optional(),
  fecha_salida: z.string().nullable().optional(),
  fecha_retorno: z.string().nullable().optional(),
  proveedor: z.number().optional(),
  notas: z.string().optional(),
}).optional().nullable();

const itemVentaSchema = z.object({
   producto_servicio: z.number().min(1, "Debe seleccionar un producto"),
   cantidad: z.coerce.number().min(1, "La cantidad debe ser al menos 1"),
   precio_unitario_venta: z.coerce.number().min(0, "El precio no puede ser negativo"),
   alojamiento_details: alojamientoSchema,
   alquiler_auto_details: alquilerAutoSchema,
   traslado_details: trasladoSchema,
   tour_actividad_details: tourActividadSchema,
   seguro_viaje_details: seguroViajeSchema,
   servicio_adicional_details: servicioAdicionalSchema,
 });

const ventaSchema = z.object({
  cliente: z.number().min(1, "Debe seleccionar un cliente"),
  moneda: z.number().min(1, "Debe seleccionar una moneda"),
  descripcion_general: z.string().min(1, "La descripción es requerida"),
  tipo_venta: z.string().default("B2C"),
  canal_origen: z.string().default("WEB"),
  items_venta: z.array(itemVentaSchema).min(1, "Debe haber al menos un item"),
});

type VentaFormData = z.infer<typeof ventaSchema>;

// --- ItemVenta Row Component ---
const ItemVentaFields = ({ index, control, remove, onOpenDetails }: any) => {
  const [productoInput, setProductoInput] = useState('');
  const debouncedProducto = useDebounce(productoInput, 500);
  const { data: productosData, isLoading: isLoadingProductos } = useApi<Paginated<ProductoServicio>>(
    `/api/productoservicio/?search=${debouncedProducto}`
  );

  const watchItems = useWatch({ control, name: 'items_venta' });
  const currentItem = watchItems[index];
  const selectedProductId = currentItem?.producto_servicio;
  const selectedProduct = productosData?.results.find(p => p.id_producto_servicio === selectedProductId);
  const productType = selectedProduct?.tipo_producto;
  const hasDetails = ['HTL', 'CAR', 'TRF', 'TOU', 'INS', 'SVC'].includes(productType || '');
  
  const getDetailStatus = () => {
    switch(productType) {
      case 'HTL': return currentItem.alojamiento_details;
      case 'CAR': return currentItem.alquiler_auto_details;
      case 'TRF': return currentItem.traslado_details;
      case 'TOU': return currentItem.tour_actividad_details;
      case 'INS': return currentItem.seguro_viaje_details;
      case 'SVC': return currentItem.servicio_adicional_details;
      default: return null;
    }
  };

  return (
    <Grid container spacing={2} sx={{ mt: 1, alignItems: 'center', borderLeft: '2px solid', borderColor: getDetailStatus() ? 'success.main' : 'transparent', pl: 1 }}>
      <Grid item xs={12} md={4}>
        <Controller
          name={`items_venta.${index}.producto_servicio`}
          control={control}
          render={({ field, fieldState: { error } }) => (
            <Autocomplete
              options={productosData?.results || []}
              loading={isLoadingProductos}
              getOptionLabel={(option) => option.nombre}
              onInputChange={(_, val, reason) => {
                if (reason === 'input') {
                  setProductoInput(val);
                }
              }}
              onChange={(_, data) => field.onChange(data?.id_producto_servicio)}
              isOptionEqualToValue={(option, value) => option.id_producto_servicio === value.id_producto_servicio}
              renderInput={(params) => (
                <TextField {...params} label="Buscar Producto/Servicio" error={!!error} helperText={error?.message} />
              )}
            />
          )}
        />
      </Grid>
      <Grid item xs={4} md={2}>
        <Controller name={`items_venta.${index}.cantidad`} control={control} render={({ field }) => <TextField {...field} type="number" label="Cantidad" fullWidth />} />
      </Grid>
      <Grid item xs={8} md={3}>
        <Controller name={`items_venta.${index}.precio_unitario_venta`} control={control} render={({ field }) => <TextField {...field} type="number" label="Precio Unitario" fullWidth />} />
      </Grid>
      <Grid item xs={12} md={2}>
        {hasDetails && (
            <Button variant="outlined" startIcon={<EditIcon />} onClick={() => onOpenDetails(index, productType)} fullWidth>
                Detalles
            </Button>
        )}
      </Grid>
      <Grid item xs={12} md={1}>
        <IconButton onClick={() => remove(index)} color="error"><DeleteIcon /></IconButton>
      </Grid>
    </Grid>
  );
};

// --- Main Page Component ---
export default function VentaManualClientPage() {
  const router = useRouter();

  const [clienteInput, setClienteInput] = useState('');
  const [monedaInput, setMonedaInput] = useState('');
  const debouncedCliente = useDebounce(clienteInput, 500);
  const debouncedMoneda = useDebounce(monedaInput, 500);

  useEffect(() => {
    console.log(`[VentaManualClientPage] debouncedCliente changed to: ${debouncedCliente} at ${new Date().toISOString()}`);
  }, [debouncedCliente]);

  useEffect(() => {
    console.log(`[VentaManualClientPage] debouncedMoneda changed to: ${debouncedMoneda} at ${new Date().toISOString()}`);
  }, [debouncedMoneda]);

  const clientesEndpoint = useMemo(() => `/api/clientes/?search=${debouncedCliente}`, [debouncedCliente]);
  const monedasEndpoint = useMemo(() => `/api/monedas/?search=${debouncedMoneda}`, [debouncedMoneda]);

  const { data: clientesData, isLoading: isLoadingClientes } = useApi<Paginated<Cliente>>(clientesEndpoint);
  const { data: monedasData, isLoading: isLoadingMonedas } = useApi<Paginated<Moneda>>(monedasEndpoint);

  const clienteOptions = useMemo(() => (clientesData?.results || []), [clientesData]);
  const monedaOptions = useMemo(() => (Array.isArray(monedasData) ? monedasData : monedasData?.results || []), [monedasData]);

  const { control, handleSubmit, setValue, formState: { errors } } = useForm<VentaFormData>({
    resolver: zodResolver(ventaSchema),
    defaultValues: {
        cliente: 0,
        moneda: 0,
        descripcion_general: '',
        tipo_venta: 'B2C',
        canal_origen: 'WEB',
        items_venta: [],
    },
  });

  const { fields, append, remove } = useFieldArray({ control, name: "items_venta" });

  const [detailsModal, setDetailsModal] = useState<{open: boolean, itemIndex: number | null, type: string | null}>({ open: false, itemIndex: null, type: null });

  const handleOpenDetails = (index: number, type: string) => {
      setDetailsModal({ open: true, itemIndex: index, type });
  };

  const handleCloseDetails = () => {
    setDetailsModal({ open: false, itemIndex: null, type: null });
  };

  const handleSaveDetails = (data: any) => {
    if (detailsModal.itemIndex !== null && detailsModal.type) {
      const fieldMap: Record<string, string> = {
        'HTL': 'alojamiento_details',
        'CAR': 'alquiler_auto_details',
        'TRF': 'traslado_details',
        'TOU': 'tour_actividad_details',
        'INS': 'seguro_viaje_details',
        'SVC': 'servicio_adicional_details',
      };
      const fieldName = fieldMap[detailsModal.type];
      if (fieldName) {
        setValue(`items_venta.${detailsModal.itemIndex}.${fieldName}`, data, { shouldValidate: true });
      }
    }
    handleCloseDetails();
  };

  const onSubmit = async (data: VentaFormData) => {
    try {
      console.log("Enviando datos de venta a la API:", data);
      const result = await apiMutate('/api/ventas/', { method: 'POST', body: data });
      console.log("Respuesta de la API:", result);
      alert(`Venta creada exitosamente! Localizador: ${result.localizador}`);
      router.push('/erp/ventas');
    } catch (error: any) {
      console.error("Error completo:", error);
      let errorMessage = 'Error al crear la venta';
      
      if (error.info) {
        // Mostrar errores de validación de forma más clara
        const errors = error.info;
        if (typeof errors === 'object') {
          const errorDetails = Object.entries(errors)
            .map(([field, messages]) => `${field}: ${Array.isArray(messages) ? messages.join(', ') : messages}`)
            .join('\n');
          errorMessage += `\n\nDetalles:\n${errorDetails}`;
        }
      } else if (error.message) {
        errorMessage += `: ${error.message}`;
      }
      
      alert(errorMessage);
    }
  };

  const items = useWatch({ control, name: "items_venta" });

  return (
    <Paper sx={{ p: 4 }}>
      <Typography variant="h4" gutterBottom>Crear Nueva Venta Manual</Typography>
      <form onSubmit={handleSubmit(onSubmit)}>
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Controller
              name="cliente"
              control={control}
              render={({ field }) => {
                const selectedCliente = clienteOptions.find(c => c.id_cliente === field.value) || null;
                return (
                  <Autocomplete
                    value={selectedCliente}
                    options={clienteOptions}
                    loading={isLoadingClientes}
                    getOptionLabel={(o) => o.get_nombre_completo || ''}
                    onInputChange={(_, val, reason) => {
                      if (reason === 'input') {
                        setClienteInput(val);
                      }
                    }}
                    onChange={(_, d) => field.onChange(d?.id_cliente)}
                    isOptionEqualToValue={(o, v) => o.id_cliente === v.id_cliente}
                    renderInput={(p) => <TextField {...p} label="Buscar Cliente" error={!!errors.cliente} helperText={errors.cliente?.message} />}
                  />
                )}
              }
            />
          </Grid>

          <Grid item xs={12} md={6}>
            <Controller
              name="moneda"
              control={control}
              render={({ field }) => {
                const selectedMoneda = monedaOptions.find(m => m.id_moneda === field.value) || null;
                return (
                  <Autocomplete
                    value={selectedMoneda}
                    options={monedaOptions}
                    loading={isLoadingMonedas}
                    getOptionLabel={(o) => `${o.nombre} (${o.codigo_iso})`}
                    onInputChange={(_, val, reason) => {
                      if (reason === 'input') {
                        setMonedaInput(val);
                      }
                    }}
                    onChange={(_, d) => field.onChange(d?.id_moneda)}
                    isOptionEqualToValue={(o, v) => o.id_moneda === v.id_moneda}
                    renderInput={(p) => <TextField {...p} label="Buscar Moneda" error={!!errors.moneda} helperText={errors.moneda?.message} />}
                  />
                )}
              }
            />
          </Grid>

          <Grid item xs={12}>
            <Controller name="descripcion_general" control={control} render={({ field }) => <TextField {...field} label="Descripción General" fullWidth error={!!errors.descripcion_general} helperText={errors.descripcion_general?.message} />} />
          </Grid>

          <Grid item xs={12}>
            <Typography variant="h6" sx={{ mt: 2 }}>Items de la Venta</Typography>
            {fields.map((item, index) => (
              <ItemVentaFields key={item.id} index={index} control={control} remove={remove} onOpenDetails={handleOpenDetails} />
            ))}
            <Button startIcon={<AddCircleOutlineIcon />} onClick={() => append({ 
              producto_servicio: 0, 
              cantidad: 1, 
              precio_unitario_venta: 0, 
              alojamiento_details: null,
              alquiler_auto_details: null,
              traslado_details: null,
              tour_actividad_details: null,
              seguro_viaje_details: null,
              servicio_adicional_details: null
            })} sx={{ mt: 2 }}>
              Añadir Item
            </Button>
          </Grid>

          <Grid item xs={12} sx={{ mt: 3 }}>
            <Button type="submit" variant="contained" color="primary">Crear Venta</Button>
          </Grid>
        </Grid>
      </form>

      {detailsModal.open && detailsModal.itemIndex !== null && (
        <>
          {detailsModal.type === 'HTL' && (
            <AlojamientoForm 
                open={detailsModal.open}
                onClose={handleCloseDetails}
                onSave={handleSaveDetails}
                alojamiento={items[detailsModal.itemIndex]?.alojamiento_details || null}
            />
          )}
          {detailsModal.type === 'CAR' && (
            <AlquilerAutoForm 
                open={detailsModal.open}
                onClose={handleCloseDetails}
                onSave={handleSaveDetails}
                alquilerAuto={items[detailsModal.itemIndex]?.alquiler_auto_details || null}
            />
          )}
          {detailsModal.type === 'TRF' && (
            <TrasladoForm 
                open={detailsModal.open}
                onClose={handleCloseDetails}
                onSave={handleSaveDetails}
                traslado={items[detailsModal.itemIndex]?.traslado_details || null}
            />
          )}
          {detailsModal.type === 'TOU' && (
            <TourActividadForm 
                open={detailsModal.open}
                onClose={handleCloseDetails}
                onSave={handleSaveDetails}
                tourActividad={items[detailsModal.itemIndex]?.tour_actividad_details || null}
            />
          )}
          {detailsModal.type === 'INS' && (
            <SeguroViajeForm 
                open={detailsModal.open}
                onClose={handleCloseDetails}
                onSave={handleSaveDetails}
                seguroViaje={items[detailsModal.itemIndex]?.seguro_viaje_details || null}
            />
          )}
          {detailsModal.type === 'SVC' && (
            <ServicioAdicionalForm 
                open={detailsModal.open}
                onClose={handleCloseDetails}
                onSave={handleSaveDetails}
                servicioAdicional={items[detailsModal.itemIndex]?.servicio_adicional_details || null}
            />
          )}
        </>
      )}
    </Paper>
  );
}
