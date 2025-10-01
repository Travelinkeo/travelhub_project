import useSWR from 'swr';
import useSWRMutation from 'swr/mutation';

// Función fetcher genérica
const fetcher = async (url: string) => {
  const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null;
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Token ${token}`;
  }

  const response = await fetch(url, { headers });
  if (!response.ok) {
    throw new Error(`Error: ${response.status}`);
  }
  return response.json();
};

// Función para normalizar el endpoint eliminando prefijo /api/
const normalizeEndpoint = (endpoint: string) => endpoint.replace(/^\/api\//, '').replace(/^\/+|\/+$/g, '');

// Hook para listar recursos
export function useApiList<T>(endpoint: string) {
  const { data, error, isLoading, mutate } = useSWR<T[]>(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/${normalizeEndpoint(endpoint)}/`, fetcher);
  return {
    data,
    error,
    isLoading,
    mutate,
  };
}

// Hook para obtener un recurso por ID
export function useApiDetail<T>(endpoint: string, id: string | number | null) {
  const { data, error, isLoading, mutate } = useSWR<T>(
    id ? `${process.env.NEXT_PUBLIC_API_BASE_URL}/api/${normalizeEndpoint(endpoint)}/${id}/` : null,
    fetcher
  );
  return {
    data,
    error,
    isLoading,
    mutate,
  };
}

// Hook para crear un recurso
export function useApiCreate<T>(endpoint: string) {
  const { trigger, isMutating, error } = useSWRMutation(
    `${process.env.NEXT_PUBLIC_API_BASE_URL}/api/${normalizeEndpoint(endpoint)}/`,
    async (url: string, { arg }: { arg: T }) => {
      const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null;
      const headers: HeadersInit = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers['Authorization'] = `Token ${token}`;
      }

      const response = await fetch(url, {
        method: 'POST',
        headers,
        body: JSON.stringify(arg),
      });
      if (!response.ok) {
        throw new Error(`Error: ${response.status}`);
      }
      return response.json();
    }
  );
  return {
    create: trigger,
    isCreating: isMutating,
    error,
  };
}

// Hook para actualizar un recurso
export function useApiUpdate<T>(endpoint: string, id: string | number) {
  const { trigger, isMutating, error } = useSWRMutation(
    `${process.env.NEXT_PUBLIC_API_BASE_URL}/api/${normalizeEndpoint(endpoint)}/${id}/`,
    async (url: string, { arg }: { arg: Partial<T> }) => {
      const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null;
      const headers: HeadersInit = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers['Authorization'] = `Token ${token}`;
      }

      const response = await fetch(url, {
        method: 'PUT',
        headers,
        body: JSON.stringify(arg),
      });
      if (!response.ok) {
        throw new Error(`Error: ${response.status}`);
      }
      return response.json();
    }
  );
  return {
    update: trigger,
    isUpdating: isMutating,
    error,
  };
}

// Hook para eliminar un recurso
export function useApiDelete(endpoint: string, id: string | number) {
  const { trigger, isMutating, error } = useSWRMutation(
    `${process.env.NEXT_PUBLIC_API_BASE_URL}/api/${normalizeEndpoint(endpoint)}/${id}/`,
    async (url: string) => {
      const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null;
      const headers: HeadersInit = {};
      if (token) {
        headers['Authorization'] = `Token ${token}`;
      }

      const response = await fetch(url, {
        method: 'DELETE',
        headers,
      });
      if (!response.ok) {
        throw new Error(`Error: ${response.status}`);
      }
      return response;
    }
  );
  return {
    deleteItem: trigger,
    isDeleting: isMutating,
    error,
  };
}