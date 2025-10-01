/**
 * @file Definiciones de tipos centralizadas para la API de TravelHub.
 *
 * Este archivo es la única fuente de verdad para las estructuras de datos
 * que se intercambian entre el backend de Django y el frontend de Next.js.
 *
 * Al definir nuestros tipos aquí, aseguramos la consistencia y prevenimos
 * errores comunes de TypeScript relacionados con datos que no coinciden.
 */

// =================================================================
// Tipos de CRM
// =================================================================

export interface Cliente {
  id_cliente?: number;
  tipo_cliente: 'PAR' | 'EMP'; // Particular o Empresa
  nombres?: string;
  apellidos?: string;
  nombre_empresa?: string;
  cedula_identidad?: string;
  email?: string;
  telefono_principal?: string;
  get_nombre_completo?: string; // Añadido para la vista de Ventas
  // Añadir otros campos del modelo de Django según sea necesario
}

export interface Proveedor {
  id_proveedor?: number;
  nombre: string;
  tipo_proveedor: string;
  nivel_proveedor: string;
  contacto_nombre?: string;
  contacto_email?: string;
  contacto_telefono?: string;
  direccion?: string;
  notas?: string;
  numero_cuenta_agencia?: string;
  condiciones_pago?: string;
  datos_bancarios?: string;
  activo: boolean;
  // Añadir otros campos del modelo de Django según sea necesario
}


// =================================================================
// Tipos de ERP
// =================================================================

export interface Moneda {
  id_moneda?: number;
  codigo_iso: string;
  nombre: string;
  simbolo?: string;
  es_moneda_local: boolean;
}

export interface Pais {
  id_pais?: number;
  codigo_iso_2: string;
  codigo_iso_3: string;
  nombre: string;
}

export interface Ciudad {
  id_ciudad?: number;
  nombre: string;
  pais: number;
  pais_detalle?: Pais;
  region_estado?: string;
}

export interface TipoCambio {
  id_tipo_cambio?: number;
  moneda_origen: number;
  moneda_origen_detalle?: Moneda;
  moneda_destino: number;
  moneda_destino_detalle?: Moneda;
  fecha_efectiva: string;
  tasa_conversion: string;
}
export interface ProductoServicio {
  id_producto_servicio: number;
  nombre: string;
  tipo_producto: string;
  descripcion?: string;
  precio_base?: string;
  activo: boolean;
  // Añadir otros campos según sea necesario
}

export type EstadoVenta = 'PEN' | 'PAR' | 'PAG' | 'CNF' | 'COM' | 'CAN';

export interface Venta {
  id_venta: number;
  localizador: string;
  cliente: number; // ID
  cliente_detalle?: Cliente;
  fecha_venta: string;
  total_venta: string;
  moneda: number; // ID
  moneda_detalle?: Moneda;
  descripcion_general?: string;
  estado?: string;
}

export type EstadoFactura = 'BOR' | 'EMI' | 'PAR' | 'PAG' | 'VEN' | 'ANU';

export interface ItemFactura {
  id_item_factura: number;
  descripcion: string;
  cantidad: string;
  precio_unitario: string;
  subtotal_item: string;
}

export interface Factura {
  id_factura: number;
  numero_factura: string;
  venta_asociada?: number; // ID
  cliente: number; // ID
  cliente_detalle?: Cliente; // The API might nest this
  fecha_emision: string;
  fecha_vencimiento?: string;
  moneda: number; // ID
  moneda_detalle?: Moneda;
  subtotal: string;
  monto_impuestos: string;
  monto_total: string;
  saldo_pendiente: string;
  estado: EstadoFactura;
  notas?: string;
  archivo_pdf?: string; // URL to the file
  items_factura?: ItemFactura[];
}

// =================================================================
// Tipos de Boletos
// =================================================================

export type FormatoDetectadoBoleto = 
  | 'PDF_KIU' | 'PDF_SAB' | 'PDF_AMA' 
  | 'TXT_KIU' | 'TXT_SAB' | 'TXT_AMA'
  | 'EML_KIU' | 'EML_GEN' | 'OTR' | 'ERR';

export type EstadoParseoBoleto = 'PEN' | 'PRO' | 'COM' | 'ERR' | 'NAP';

/**
 * Define la estructura esperada de los datos extraídos de un boleto.
 * Permite flexibilidad para campos no definidos explícitamente.
 */
export interface DatosParseadosBoleto {
  numero_boleto?: string;
  nombre_pasajero_completo?: string;
  ruta_vuelo?: string;
  fecha_emision_boleto?: string;
  aerolinea_emisora?: string;
  localizador_pnr?: string;
  tarifa_base?: string;
  impuestos_total_calculado?: string;
  total_boleto?: string;
  [key: string]: any; // Permite otros campos no definidos
}

export interface BoletoImportado {
  id_boleto_importado: number;
  archivo_boleto: string; // URL to the file
  fecha_subida: string;
  formato_detectado: FormatoDetectadoBoleto;
  datos_parseados?: DatosParseadosBoleto;
  estado_parseo: EstadoParseoBoleto;
  log_parseo?: string;
  numero_boleto?: string;
  nombre_pasajero_completo?: string;
  nombre_pasajero_procesado?: string;
  ruta_vuelo?: string;
  fecha_emision_boleto?: string;
  aerolinea_emisora?: string;
  direccion_aerolinea?: string;
  agente_emisor?: string;
  foid_pasajero?: string;
  localizador_pnr?: string;
  tarifa_base?: string; // Use string for decimals to avoid precision issues
  impuestos_descripcion?: string;
  impuestos_total_calculado?: string;
  total_boleto?: string;
  exchange_monto?: string;
  void_monto?: string;
  fee_servicio?: string;
  igtf_monto?: string;
  comision_agencia?: string;
  venta_asociada?: number; // ID of the related Venta
  archivo_pdf_generado?: string; // URL to the file
}


// Añadir aquí otras interfaces para los modelos (Moneda, Pais, etc.)


// =================================================================
// Tipos de Cotizaciones
// =================================================================

export interface User {
  id: number;
  username: string;
  first_name?: string;
  last_name?: string;
  get_full_name?: string;
}

export type EstadoCotizacion = 'BOR' | 'ENV' | 'ACE' | 'REC' | 'VEN';
export type TipoItemCotizacion = 'VUE' | 'ALO' | 'ACT' | 'SEG' | 'OTR';

export interface ItemCotizacion {
  id_item_cotizacion?: number;
  cotizacion?: number;
  tipo_item: TipoItemCotizacion;
  descripcion: string;
  detalles_json?: any; // Could be a discriminated union for more type safety
  costo: string;
}

export interface ServicioAdicionalDetalle {
  id_servicio_adicional_detalle: number;
  venta: number;
  descripcion: string;
  costo: string;
  precio_venta: string;
  proveedor: number | null;
}

export interface Cotizacion {
  id_cotizacion?: number;
  cliente: number;
  cliente_detalle?: Cliente;
  fecha_cotizacion: string;
  total_cotizacion: string;
  estado: EstadoCotizacion;
  descripcion?: string;
  // Añadir otros campos según sea necesario
}

export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

