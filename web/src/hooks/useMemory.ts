import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';
import { useState, useEffect } from 'react';

export function usePatternSearch(query: string, enabled = true) {
  return useQuery({
    queryKey: ['patterns', query],
    queryFn: () => api.queryPatterns(query),
    enabled: enabled && query.length >= 50, // Only search with sufficient text
    staleTime: 60000, // Cache for 1 minute
  });
}

export function useSuggestions(requirements: string) {
  return useQuery({
    queryKey: ['suggestions', requirements],
    queryFn: () => api.getSuggestions(requirements),
    enabled: requirements.length >= 50,
    staleTime: 60000,
  });
}

// Debounced search hook
export function useDebouncedPatternSearch(query: string, delay = 500) {
  const [debouncedQuery, setDebouncedQuery] = useState(query);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(query);
    }, delay);

    return () => clearTimeout(timer);
  }, [query, delay]);

  return usePatternSearch(debouncedQuery, debouncedQuery.length >= 50);
}
