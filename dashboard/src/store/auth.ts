import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { apiClient } from '@/api/client';
import type { QuotaOut } from '@/types/api';

interface AuthStore {
  apiKey: string | null;
  email: string | null;
  tier: string | null;
  quota: { used: number; total: number } | null;
  setApiKey: (key: string) => void;
  clearAuth: () => void;
  fetchQuota: () => Promise<void>;
}

export const useAuthStore = create<AuthStore>()(
  persist(
    (set, get) => ({
      apiKey: null,
      email: null,
      tier: null,
      quota: null,

      setApiKey: (key: string) => {
        set({ apiKey: key });
        // Fetch quota after key is set
        get().fetchQuota();
      },

      clearAuth: () => {
        set({ apiKey: null, email: null, tier: null, quota: null });
      },

      fetchQuota: async () => {
        const key = get().apiKey;
        if (!key) return;
        try {
          const { data } = await apiClient.get<QuotaOut>('/usage');
          set({
            email: data.tier, // Using tier as email fallback for now
            tier: data.tier,
            quota: {
              used: data.used_this_month,
              total: data.monthly_quota,
            },
          });
        } catch (err) {
          console.error('Failed to fetch quota:', err);
        }
      },
    }),
    {
      name: 'qmol-auth',
      partialize: (state) => ({ apiKey: state.apiKey }),
    }
  )
);
