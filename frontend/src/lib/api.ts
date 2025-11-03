const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || process.env.NEXT_PUBLIC_API_BASE_URL || 'http://127.0.0.1:8000';

function getAuthHeaders() {
  if (typeof window === 'undefined') return {};
  
  // Intentar múltiples nombres de token
  const token = localStorage.getItem('auth_token') 
    || localStorage.getItem('access_token')
    || localStorage.getItem('token');
  
  return token ? { 'Authorization': `Bearer ${token}` } : {};
}

export async function apiMutate(endpoint: string, options: RequestInit = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  
  // Stringify body si no lo está
  const preparedOptions = options.body && typeof options.body !== 'string' 
    ? { ...options, body: JSON.stringify(options.body) }
    : options;
  
  const response = await fetch(url, {
    ...preparedOptions,
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
      ...preparedOptions.headers,
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    const error: any = new Error(`HTTP error! status: ${response.status}`);
    error.response = errorData;
    error.status = response.status;
    throw error;
  }

  return response.json();
}

export const api = {
  get: (endpoint: string) => apiMutate(endpoint, { method: 'GET' }),
  post: (endpoint: string, data: any) => apiMutate(endpoint, { method: 'POST', body: JSON.stringify(data) }),
  put: (endpoint: string, data: any) => apiMutate(endpoint, { method: 'PUT', body: JSON.stringify(data) }),
  patch: (endpoint: string, data: any) => apiMutate(endpoint, { method: 'PATCH', body: JSON.stringify(data) }),
  delete: (endpoint: string) => apiMutate(endpoint, { method: 'DELETE' }),
};

export default api;