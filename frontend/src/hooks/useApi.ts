import React from 'react';
import useSWR, { SWRConfiguration } from 'swr';

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;

// Simplified fetcher: always fetches a single URL.
const fetcher = async (url: string) => {
  const fullUrl = `${apiBaseUrl}${url}`;
  console.log(`[useApi] Fetching: ${fullUrl}`);
  
  const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null;
  const headers: HeadersInit = {};
  if (token) {
    headers['Authorization'] = `Token ${token}`;
  }
  
  const res = await fetch(fullUrl, { headers });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ message: 'Error al leer la respuesta de la API.' }));
    const error = new Error(errorData.detail || errorData.message || 'Ocurrió un error en la petición a la API.');
    (error as any).info = errorData;
    (error as any).status = res.status;
    if (res.status === 429) {
      console.error(`[useApi] Rate limit error (429) for: ${fullUrl}`);
    } else {
      console.error(`[useApi] API error (${res.status}) for: ${fullUrl}`, errorData);
    }
    throw error;
  }

  const data = await res.json();
  console.log(`[useApi] Success: ${fullUrl}`);

  // If the response is paginated, return the whole paginated object.
  // Otherwise, return the data as is.
  return data;
};

// useApi hook with calmer revalidation settings.
export function useApi<T>(endpoint: string | null, config?: SWRConfiguration) {
  const { data, error, isLoading, mutate } = useSWR<T>(
    endpoint,
    (url) => fetcher(url),
    {
      // Optimized settings for better performance
      revalidateOnFocus: false,
      revalidateOnReconnect: false,
      revalidateOnMount: true,
      revalidateIfStale: false,
      keepPreviousData: true,
      dedupingInterval: 2000, // 2 seconds for faster search responses
      focusThrottleInterval: 5000,
      errorRetryCount: 0, // No retries for faster error handling
      shouldRetryOnError: () => false, // Disable all retries
      onError: (err) => {
        // Removed logging to reduce noise
      },
      onSuccess: (data) => {
        // Removed logging to reduce noise
      },
      ...config, // Allow overriding defaults
    }
  );

  return {
    data,
    error,
    isLoading,
    mutate,
  };
}