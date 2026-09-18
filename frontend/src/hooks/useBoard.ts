// One hook per API resource; mutations invalidate the resource root (MITA Finance convention).
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { fetchJson, postJson } from '@/lib/api';
import type {
  ApplicationDetail,
  ApplicationIn,
  ApplicationRow,
  Campaign,
  CampaignIn,
  Dashboard,
  Meta,
  Status,
} from '@/lib/types';

export function useMeta() {
  return useQuery({ queryKey: ['meta'], queryFn: () => fetchJson<Meta>('/api/meta'), staleTime: Infinity });
}

export function useCampaigns() {
  return useQuery({ queryKey: ['campaigns'], queryFn: () => fetchJson<Campaign[]>('/api/campaigns') });
}

export function useCreateCampaign() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: CampaignIn) => postJson<Campaign>('/api/campaigns', body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['campaigns'] }),
  });
}

export function useActivateCampaign() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => postJson<Campaign>(`/api/campaigns/${id}/activate`, {}),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['campaigns'] });
      qc.invalidateQueries({ queryKey: ['meta'] }); // tz may follow the active campaign
    },
  });
}

export function useDashboard(campaignId: number | null) {
  return useQuery({
    queryKey: ['campaigns', campaignId, 'dashboard'],
    queryFn: () => fetchJson<Dashboard>(`/api/campaigns/${campaignId}/dashboard`),
    enabled: campaignId !== null,
  });
}

export function useApplications(campaignId: number | null) {
  return useQuery({
    queryKey: ['campaigns', campaignId, 'applications'],
    queryFn: () => fetchJson<ApplicationRow[]>(`/api/campaigns/${campaignId}/applications`),
    enabled: campaignId !== null,
  });
}

export function useApplication(id: number) {
  return useQuery({
    queryKey: ['applications', id],
    queryFn: () => fetchJson<ApplicationDetail>(`/api/applications/${id}`),
  });
}

function useApplicationMutation<V>(fn: (v: V) => Promise<ApplicationDetail>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: (detail) => {
      qc.setQueryData(['applications', detail.application_id], detail);
      qc.invalidateQueries({ queryKey: ['campaigns'] });
    },
  });
}

export function useCreateApplication() {
  return useApplicationMutation((body: ApplicationIn) =>
    postJson<ApplicationDetail>('/api/applications', body),
  );
}

export function useAddEvent(id: number) {
  return useApplicationMutation((body: { event_type: string; occurred_at: string; summary?: string | null }) =>
    postJson<ApplicationDetail>(`/api/applications/${id}/events`, body),
  );
}

export function useSetStatus(id: number) {
  return useApplicationMutation((body: { user_status: Status | null; excluded_reason?: string | null }) =>
    postJson<ApplicationDetail>(`/api/applications/${id}/status`, body),
  );
}
