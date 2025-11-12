// API functions para boletería
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const getAuthHeaders = () => {
  const token = localStorage.getItem('accessToken');
  return {
    'Content-Type': 'application/json',
    'Authorization': token ? `Bearer ${token}` : '',
  };
};

export const validarBoleto = async (boletoId: number) => {
  const response = await fetch(`${API_URL}/api/boletos-importados/${boletoId}/validar/`, {
    method: 'POST',
    headers: getAuthHeaders(),
  });
  return response.json();
};

export const obtenerDashboard = async () => {
  const response = await fetch(`${API_URL}/api/boletos-importados/dashboard/`, {
    headers: getAuthHeaders(),
  });
  return response.json();
};

export const obtenerReporteComisiones = async (fechaInicio?: string, fechaFin?: string) => {
  const params = new URLSearchParams();
  if (fechaInicio) params.append('fecha_inicio', fechaInicio);
  if (fechaFin) params.append('fecha_fin', fechaFin);
  
  const response = await fetch(
    `${API_URL}/api/boletos-importados/reporte_comisiones/?${params}`,
    { headers: getAuthHeaders() }
  );
  return response.json();
};

export const buscarBoletos = async (filtros: any) => {
  const params = new URLSearchParams();
  Object.entries(filtros).forEach(([key, value]) => {
    if (value) params.append(key, String(value));
  });
  
  const response = await fetch(
    `${API_URL}/api/boletos-importados/busqueda_avanzada/?${params}`,
    { headers: getAuthHeaders() }
  );
  return response.json();
};

export const solicitarAnulacion = async (data: any) => {
  const response = await fetch(`${API_URL}/api/anulaciones-boletos/`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(data),
  });
  return response.json();
};

export const aprobarAnulacion = async (anulacionId: number) => {
  const response = await fetch(
    `${API_URL}/api/anulaciones-boletos/${anulacionId}/aprobar/`,
    {
      method: 'POST',
      headers: getAuthHeaders(),
    }
  );
  return response.json();
};

export const obtenerHistorial = async (boletoId: number) => {
  const response = await fetch(
    `${API_URL}/api/historial-cambios-boletos/?boleto=${boletoId}`,
    { headers: getAuthHeaders() }
  );
  return response.json();
};
