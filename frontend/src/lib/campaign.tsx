// Which campaign the whole UI is looking at: localStorage, else the server's active one.
import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { useCampaigns } from '@/hooks/useBoard';
import type { Campaign } from '@/lib/types';

const KEY = 'jobpilot.campaign';

interface Value {
  campaigns: Campaign[];
  current: Campaign | null;
  select: (id: number) => void;
  loaded: boolean;
  error: Error | null;
  refetch: () => void;
}

const Ctx = createContext<Value>({
  campaigns: [],
  current: null,
  select: () => {},
  loaded: false,
  error: null,
  refetch: () => {},
});

export function CampaignProvider({ children }: { children: ReactNode }) {
  const { data, isSuccess, error, refetch } = useCampaigns();
  const [id, setId] = useState<number | null>(() => {
    const v = localStorage.getItem(KEY);
    return v ? Number(v) : null;
  });
  useEffect(() => {
    if (!data) return;
    const known = id !== null && data.some((c) => c.campaign_id === id);
    if (!known) setId(data.find((c) => c.is_active)?.campaign_id ?? data[0]?.campaign_id ?? null);
  }, [data, id]);
  const value = useMemo<Value>(
    () => ({
      campaigns: data ?? [],
      current: data?.find((c) => c.campaign_id === id) ?? null,
      select: (next) => {
        localStorage.setItem(KEY, String(next));
        setId(next);
      },
      loaded: isSuccess,
      error,
      refetch,
    }),
    [data, id, isSuccess, error, refetch],
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components -- provider and hook belong together
export function useCampaign() {
  return useContext(Ctx);
}
