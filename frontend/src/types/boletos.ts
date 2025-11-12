// Types para el sistema de boletería
export interface Boleto {
  id_boleto_importado: number;
  numero_boleto: string;
  nombre_pasajero_procesado: string;
  aerolinea_emisora: string;
  fecha_emision_boleto: string;
  total_boleto: number;
  estado_parseo: 'PEN' | 'PRO' | 'COM' | 'ERR' | 'NAP';
  localizador_pnr: string;
}

export interface ResultadoValidacion {
  valido: boolean;
  errores: string[];
  advertencias: string[];
}

export interface MetricasDashboard {
  procesados: {
    hoy: number;
    semana: number;
    mes: number;
  };
  tasas_exito_gds: Array<{
    formato_detectado: string;
    total: number;
    exitosos: number;
    tasa_exito: number;
  }>;
  pendientes: number;
  errores: number;
  top_aerolineas: Array<{
    aerolinea_emisora: string;
    cantidad: number;
  }>;
}

export interface ReporteComisiones {
  periodo: {
    fecha_inicio: string;
    fecha_fin: string;
  };
  por_aerolinea: Array<{
    aerolinea: string;
    cantidad_boletos: number;
    total_ventas: string;
    total_comisiones: string;
    comision_promedio: string;
  }>;
  totales: {
    total_boletos: number;
    total_ventas: string;
    total_comisiones: string;
  };
}

export interface HistorialCambio {
  id_historial: number;
  boleto: number;
  tipo_cambio: 'CF' | 'CP' | 'RE' | 'CA' | 'CO' | 'OT';
  descripcion: string;
  costo_cambio: number;
  fecha_cambio: string;
}

export interface Anulacion {
  id_anulacion: number;
  boleto: number;
  tipo_anulacion: 'VOL' | 'INV' | 'CAM';
  estado: 'SOL' | 'PRO' | 'APR' | 'REC' | 'REE';
  motivo: string;
  monto_original: number;
  penalidad_aerolinea: number;
  fee_agencia: number;
  monto_reembolso: number;
  fecha_solicitud: string;
}
