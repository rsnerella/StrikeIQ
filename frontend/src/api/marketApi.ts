import api from './client';
import { validateTokenAndRedirect } from '@/utils/auth';

export interface ExpiryResponse {
  symbol: string;
  expiries: string[];
}

export const fetchAvailableExpiries = async (symbol: string): Promise<string[]> => {
  // Validate token before making request
  if (!validateTokenAndRedirect()) {
    return [];
  }

  try {
    const res = await api.get(`/v1/market/expiries?symbol=${symbol}`)
    return res.data.expiries ?? []
  } catch {
    return []
  }
};
