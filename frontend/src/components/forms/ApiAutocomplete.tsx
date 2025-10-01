'use client';

import React, { useMemo, useState, useCallback } from 'react';
import { Autocomplete, TextField, CircularProgress } from '@mui/material';
import { useApi } from '@/hooks/useApi';
import { useDebounce } from '@/hooks/useDebounce';

interface ApiAutocompleteProps<T> {
  endpoint: string;
  label: string;
  value: T[keyof T] | null;
  onChange: (value: T[keyof T] | null) => void;
  optionIdField: keyof T;
  optionLabelField: keyof T | ((option: T) => string);
  error?: boolean;
  helperText?: string;
  searchParam?: string;
  enableSearch?: boolean;
}

const ApiAutocomplete = React.forwardRef<
  HTMLDivElement,
  ApiAutocompleteProps<any>
>(
  (
    {
      endpoint,
      label,
      value,
      onChange,
      optionIdField,
      optionLabelField,
      error,
      helperText,
      searchParam = 'search',
      enableSearch = false,
    },
    ref
  ) => {
    const [searchInput, setSearchInput] = useState('');
    const debouncedSearch = useDebounce(searchInput, 500);

    const apiEndpoint = useMemo(() => {
      if (enableSearch) {
        return `${endpoint}?${searchParam}=${debouncedSearch}`;
      }
      return endpoint;
    }, [endpoint, enableSearch, searchParam, debouncedSearch]);

    const { data, isLoading } = useApi<any>(apiEndpoint);

    const options = useMemo(() => {
      if (!data) return [];
      return Array.isArray(data) ? data : data.results || [];
    }, [data]);

    const selectedValue = useMemo(
      () => options.find((option: any) => option[optionIdField] === value) || null,
      [options, value, optionIdField]
    );

    const handleChange = useCallback((_event: any, newValue: any) => {
      onChange(newValue ? newValue[optionIdField] : null);
    }, [onChange, optionIdField]);

    const handleInputChange = useCallback((_event: any, newInputValue: string, reason: string) => {
      if (enableSearch && reason === 'input') {
        setSearchInput(newInputValue);
      }
    }, [enableSearch]);

    return (
      <Autocomplete
        ref={ref}
        options={options}
        loading={isLoading}
        value={selectedValue}
        onChange={handleChange}
        onInputChange={handleInputChange}
        getOptionLabel={(option: any) => {
          if (typeof optionLabelField === 'function') {
            return optionLabelField(option) || '';
          }
          return String(option[optionLabelField] || '');
        }}
        isOptionEqualToValue={(option: any, val: any) => 
          option && val && option[optionIdField] === val[optionIdField]
        }
        getOptionKey={(option: any) => option[optionIdField] || Math.random()}
        filterOptions={(x) => x} // Disable client-side filtering when server-side is active
        renderInput={(params) => (
          <TextField
            {...params}
            label={label}
            error={error}
            helperText={helperText}
            InputProps={{
              ...params.InputProps,
              endAdornment: (
                <>
                  {isLoading ? <CircularProgress color="inherit" size={20} /> : null}
                  {params.InputProps.endAdornment}
                </>
              ),
            }}
          />
        )}
      />
    );
  }
);

ApiAutocomplete.displayName = 'ApiAutocomplete';

export default ApiAutocomplete;
