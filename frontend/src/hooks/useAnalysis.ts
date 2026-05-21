import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { AnalysisResponse } from '@/types';

export function useAnalysis(type: string | null) {
  return useQuery<AnalysisResponse>({
    queryKey: ['analysis', type],
    queryFn: () => api.runAnalysis(type!),
    enabled: !!type,
    staleTime: 60_000,
  });
}
