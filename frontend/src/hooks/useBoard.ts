// One hook per API resource; mutations invalidate the resource root (MITA Finance convention).
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { fetchJson, postJson } from '@/lib/api';
import type {
  ApplicationDetail,
  ApplicationIn,
  ApplicationPatch,
  ApplicationRow,
  Campaign,
  CampaignDeleteOut,
  CampaignIn,
  Dashboard,
  DeleteOut,
  EventIn,
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
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['campaigns'] });
      qc.invalidateQueries({ queryKey: ['meta'] });
    },
  });
}

export function useUpdateCampaign() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: number; body: CampaignIn }) =>
      fetchJson<Campaign>(`/api/campaigns/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['campaigns'] });
      qc.invalidateQueries({ queryKey: ['meta'] }); // region pack (tz) may change
    },
  });
}

export function useDeleteCampaign() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => fetchJson<CampaignDeleteOut>(`/api/campaigns/${id}`, { method: 'DELETE' }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['campaigns'] });
      qc.invalidateQueries({ queryKey: ['meta'] });
    },
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

export function useUpdateApplication(id: number) {
  return useApplicationMutation((body: ApplicationPatch) =>
    fetchJson<ApplicationDetail>(`/api/applications/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
  );
}

export function useDeleteApplication(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => fetchJson<DeleteOut>(`/api/applications/${id}`, { method: 'DELETE' }),
    onSuccess: () => {
      // Drop the row from cached lists right away so the pipeline table doesn't flash the deleted row.
      qc.setQueriesData<ApplicationRow[]>({ queryKey: ['campaigns'] }, (old) =>
        Array.isArray(old) ? old.filter((r) => r.application_id !== id) : old,
      );
      qc.removeQueries({ queryKey: ['applications', id] });
      qc.invalidateQueries({ queryKey: ['campaigns'] });
    },
  });
}

export function useAddEvent(id: number) {
  // event_type stays `string` until pages type their state as EventType; the server validates the enum.
  return useApplicationMutation((body: { event_type: string; occurred_at: string; summary?: string | null }) =>
    postJson<ApplicationDetail>(`/api/applications/${id}/events`, body),
  );
}

export function useUpdateEvent(appId: number) {
  return useApplicationMutation(({ eventId, body }: { eventId: number; body: EventIn }) =>
    fetchJson<ApplicationDetail>(`/api/applications/${appId}/events/${eventId}`, {
      method: 'PATCH',
      body: JSON.stringify(body),
    }),
  );
}

export function useDeleteEvent(appId: number) {
  return useApplicationMutation((eventId: number) =>
    fetchJson<ApplicationDetail>(`/api/applications/${appId}/events/${eventId}`, { method: 'DELETE' }),
  );
}

export function useClearNextAction(appId: number) {
  return useApplicationMutation<void>(() =>
    fetchJson<ApplicationDetail>(`/api/applications/${appId}/next-action`, { method: 'DELETE' }),
  );
}

export function useSetStatus(id: number) {
  return useApplicationMutation((body: { user_status: Status | null; excluded_reason?: string | null }) =>
    postJson<ApplicationDetail>(`/api/applications/${id}/status`, body),
  );
}
