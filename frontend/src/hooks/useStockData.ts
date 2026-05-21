import { useMutation } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { useAppStore } from '@/store/appStore';
import type { FetchResponse } from '@/types';

export function useStockData() {
  const { setStock, setDataLoaded } = useAppStore();

  return useMutation<FetchResponse, Error, { code: string; source: string }>({
    mutationFn: ({ code, source }) => api.fetchStockData(code, source),
    onSuccess: (data) => {
      if (data.success && data.kpis) {
        setStock(data.kpis.stock_code, data.kpis.stock_name);
        setDataLoaded(true);
      }
    },
  });
}
