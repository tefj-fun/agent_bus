import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/client';

export function useJobs(limit = 50) {
  return useQuery({
    queryKey: ['jobs', limit],
    queryFn: () => api.getJobs(limit),
    refetchInterval: 10000, // Refetch every 10 seconds
  });
}

export function useJob(jobId: string | undefined) {
  return useQuery({
    queryKey: ['job', jobId],
    queryFn: () => api.getJob(jobId!),
    enabled: !!jobId,
    refetchInterval: (data) => {
      // Stop polling when job is completed or failed
      if (data?.state?.data?.status === 'completed' || data?.state?.data?.status === 'failed') {
        return false;
      }
      return 5000; // Poll every 5 seconds
    },
  });
}

export function usePrd(jobId: string | undefined) {
  return useQuery({
    queryKey: ['prd', jobId],
    queryFn: () => api.getPrd(jobId!),
    enabled: !!jobId,
    retry: false, // Don't retry if PRD doesn't exist yet
  });
}

export function usePlan(jobId: string | undefined) {
  return useQuery({
    queryKey: ['plan', jobId],
    queryFn: () => api.getPlan(jobId!),
    enabled: !!jobId,
    retry: false,
  });
}

export function useArtifacts(jobId: string | undefined) {
  return useQuery({
    queryKey: ['artifacts', jobId],
    queryFn: () => api.getArtifacts(jobId!),
    enabled: !!jobId,
  });
}

export function useCreateProject() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: api.createProject,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
    },
  });
}

export function useApprovePrd(jobId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (notes?: string) => api.approvePrd(jobId, notes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['job', jobId] });
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
    },
  });
}

export function useRequestChanges(jobId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (notes: string) => api.requestChanges(jobId, notes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['job', jobId] });
      queryClient.invalidateQueries({ queryKey: ['prd', jobId] });
    },
  });
}
