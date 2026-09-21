import { Plus } from 'lucide-react';
import { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { ApplicationForm } from '@/components/ApplicationForm';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { Pill, SourceBadge, StatusChip } from '@/components/ui/Chips';
import { EmptyState } from '@/components/ui/EmptyState';
import { Field, inputClass } from '@/components/ui/Field';
import { PageHeader } from '@/components/ui/PageHeader';
import { PaperCard } from '@/components/ui/PaperCard';
import { Segmented } from '@/components/ui/Segmented';
import { useApplications, useCreateApplication, useMeta } from '@/hooks/useBoard';
import { ApiError, apiMessage } from '@/lib/api';
import { useCampaign } from '@/lib/campaign';
import { daysAgo, fmtDateTime } from '@/lib/format';
import { useT } from '@/lib/i18n';
import { groupOf, STATUS_GROUPS, STATUS_ORDER, type StatusGroup } from '@/lib/status';
import { useToast } from '@/lib/toast';
import type { ApplicationRow, Track } from '@/lib/types';

const ALL_TRACKS = 'all';
const ALL_GROUPS = 'all';
const GROUP_KEYS = Object.keys(STATUS_GROUPS) as StatusGroup[];
type GroupFilter = StatusGroup | typeof ALL_GROUPS;

function AddForm({ campaignId, defaultTrack, tz, onCancel }: { campaignId: number; defaultTrack: Track; tz: string; onCancel: () => void }) {
  const { t } = useT();
  const meta = useMeta();
  const create = useCreateApplication();
  const toast = useToast();
  const [formKey, setFormKey] = useState(0);

  const err = create.error;
  const duplicateId =
    err instanceof ApiError && err.code === 'application_exists' && typeof err.extra?.existing_application_id === 'number'
      ? err.extra.existing_application_id
      : null;

  return (
    <PaperCard>
      <ApplicationForm
        key={formKey}
        mode="add"
        tz={tz}
        tracks={meta.data?.tracks ?? []}
        statuses={meta.data?.statuses ?? []}
        defaultTrack={defaultTrack}
        busy={create.isPending}
        error={
          create.isError ? (
            <Alert tone="error">
              {apiMessage(t, err)}
              {duplicateId !== null ? (
                <>
                  {' '}
                  <Link to={`/pipeline/${duplicateId}`} className="underline">{t('application.duplicate.view_existing')}</Link>
                </>
              ) : null}
            </Alert>
          ) : undefined
        }
        onSubmit={(v) =>
          create.mutate(
            {
              campaign_id: campaignId,
              company_name: v.company_name,
              role: v.role,
              track: v.track,
              job_url: v.job_url,
              notes: v.notes,
              initial_status: v.initial_status,
            },
            {
              onSuccess: (detail) => {
                setFormKey((k) => k + 1);
                toast.show(t('toast.application_added'), { to: `/pipeline/${detail.application_id}`, toLabel: t('common.open') });
              },
            },
          )
        }
        onCancel={onCancel}
      />
    </PaperCard>
  );
}

function Row({ row, tz }: { row: ApplicationRow; tz: string }) {
  const { t, lang } = useT();
  const navigate = useNavigate();
  const next = row.deadline_at ?? row.next_action_due;
  return (
    <tr
      onClick={(e) => {
        if ((e.target as Element).closest('a,button,input,select')) return;
        if (window.getSelection()?.toString()) return;
        navigate(`/pipeline/${row.application_id}`);
      }}
      className={[row.is_ghosted ? 'ghosted' : '', 'cursor-pointer transition-colors hover:bg-cream-50/80 focus-within:bg-cream-50/80'].join(' ')}
    >
      <td className="px-4 py-3 text-ink-900">
        <Link className="font-medium hover:underline" to={`/pipeline/${row.application_id}`}>{row.company}</Link>
        {row.is_ghosted && row.last_event_at ? (
          <div className="text-[11px] italic text-ink-500">{t('pipeline.ghosted', { n: daysAgo(row.last_event_at) })}</div>
        ) : null}
      </td>
      <td className="px-4 py-3 text-ink-700">
        {row.role ?? t('common.none')} <Pill>{t(`track.${row.track}`)}</Pill>
      </td>
      <td className="px-4 py-3"><StatusChip status={row.status} autoStatus={row.auto_status} /></td>
      <td className="px-4 py-3 text-ink-700">
        {row.last_event_type ? (
          <>
            {t(`event.${row.last_event_type}`)}
            {row.last_event_at ? <div className="font-mono text-[11px] text-ink-500">{fmtDateTime(row.last_event_at, tz, lang)}</div> : null}
          </>
        ) : t('common.none')}
      </td>
      <td className="px-4 py-3 font-mono text-xs text-ink-700">
        {next ? fmtDateTime(next, tz, lang) : t('common.none')}
        {row.next_action ? <div className="font-sans text-[11px] text-ink-500">{row.next_action}</div> : null}
      </td>
      <td className="px-4 py-3"><SourceBadge source="manual" /></td>
    </tr>
  );
}

export function PipelinePage() {
  const { t } = useT();
  const { current, loaded } = useCampaign();
  const meta = useMeta();
  const apps = useApplications(current?.campaign_id ?? null);
  const [adding, setAdding] = useState(false);
  const [params, setParams] = useSearchParams();
  const tz = current?.tz ?? meta.data?.tz ?? 'UTC';

  const groupParam = params.get('group');
  const activeGroup: GroupFilter = GROUP_KEYS.includes(groupParam as StatusGroup) ? (groupParam as StatusGroup) : ALL_GROUPS;
  const track = params.get('track') ?? ALL_TRACKS;
  const keyword = params.get('q') ?? '';
  const setParam = (key: string, value: string, def: string) =>
    setParams(
      (prev) => {
        if (value === def) prev.delete(key);
        else prev.set(key, value);
        return prev;
      },
      { replace: true },
    );
  const setGroup = (g: GroupFilter) => setParam('group', g, ALL_GROUPS);
  const setTrack = (v: string) => setParam('track', v, ALL_TRACKS);
  const setKeyword = (v: string) => setParam('q', v, '');

  if (loaded && !current) {
    return <EmptyState title={t('settings.campaigns.empty')} action={<Link className="text-sm underline" to="/settings">{t('nav.settings')}</Link>} />;
  }
  const rows = apps.data ?? [];
  const cols = ['company', 'role', 'status', 'last_event', 'next', 'source'] as const;
  const keywordLower = keyword.trim().toLowerCase();
  const filteredRows = rows.filter(
    (r) =>
      (activeGroup === ALL_GROUPS || groupOf(r.status) === activeGroup) &&
      (track === ALL_TRACKS || r.track === track) &&
      (!keywordLower || `${r.company} ${r.role ?? ''}`.toLowerCase().includes(keywordLower)),
  );
  const clearFilters = () => setParams({}, { replace: true });
  const restStatuses = STATUS_ORDER.filter(
    (s) => (activeGroup === ALL_GROUPS || groupOf(s) === activeGroup) && !filteredRows.some((r) => r.status === s),
  );

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow={t('pipeline.eyebrow')}
        title={t('pipeline.title')}
        hint={current ? `${current.name} · ${t('common.applications_count', { n: rows.length })}` : undefined}
        actions={
          <Button onClick={() => setAdding(true)} leadingIcon={<Plus size={16} />} disabled={!current}>
            {t('pipeline.add')}
          </Button>
        }
      />
      {adding && current ? (
        <AddForm campaignId={current.campaign_id} defaultTrack={current.kind} tz={tz} onCancel={() => setAdding(false)} />
      ) : null}
      {apps.isLoading ? <p className="text-sm text-ink-500">{t('common.loading')}</p> : null}
      {apps.isError ? (
        <Alert tone="error">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span>{apiMessage(t, apps.error)}</span>
            <Button variant="outline" size="sm" onClick={() => apps.refetch()}>{t('common.retry')}</Button>
          </div>
        </Alert>
      ) : null}
      {apps.isSuccess && rows.length === 0 ? (
        <EmptyState title={t('pipeline.empty')} />
      ) : apps.isSuccess ? (
        <>
          <Segmented<GroupFilter>
            value={activeGroup}
            onChange={setGroup}
            ariaLabel={t('pipeline.col.status')}
            options={[
              { value: ALL_GROUPS, label: t('pipeline.filter.all'), count: rows.length },
              ...GROUP_KEYS.map((g) => ({
                value: g,
                label: t(`group.${g}`),
                count: rows.filter((r) => groupOf(r.status) === g).length,
              })),
            ]}
          />
          <div className="flex flex-wrap items-end gap-3">
            <Field label={t('pipeline.filter.track')}>
              <select className={inputClass} value={track} onChange={(e) => setTrack(e.target.value)}>
                <option value={ALL_TRACKS}>{t('pipeline.filter.all')}</option>
                {(meta.data?.tracks ?? []).map((tr) => (
                  <option key={tr} value={tr}>{t(`track.${tr}`)}</option>
                ))}
              </select>
            </Field>
            <div className="min-w-56 flex-1">
              <Field label={t('pipeline.filter.keyword_placeholder')}>
                <input
                  className={inputClass}
                  value={keyword}
                  placeholder={t('pipeline.filter.keyword_placeholder')}
                  onChange={(e) => setKeyword(e.target.value)}
                />
              </Field>
            </div>
          </div>
          {filteredRows.length === 0 ? (
            <EmptyState
              title={t('pipeline.filter_empty.title')}
              hint={t('pipeline.filter_empty.body')}
              action={<Button variant="ghost" size="sm" onClick={clearFilters}>{t('pipeline.filter.clear')}</Button>}
            />
          ) : (
            <div className="overflow-hidden rounded-2xl border border-cream-200 bg-cream-100">
              <table className="w-full text-sm">
                <thead className="bg-cream-200/60 text-left text-xs uppercase tracking-wide text-ink-500">
                  <tr>
                    {cols.map((c) => (
                      <th key={c} className="px-4 py-2 font-semibold">{t(`pipeline.col.${c}`)}</th>
                    ))}
                  </tr>
                </thead>
                {STATUS_ORDER.map((status) => {
                  const group = filteredRows.filter((r) => r.status === status);
                  if (group.length === 0) return null;
                  return (
                    <tbody key={status} className="divide-y divide-cream-200 border-t border-cream-200">
                      <tr className="bg-cream-50/60">
                        <td colSpan={cols.length} className="px-4 py-1.5">
                          <button
                            type="button"
                            onClick={() => setGroup(groupOf(status))}
                            className="-mx-1 inline-flex items-center gap-2 rounded-lg px-1 hover:bg-cream-100"
                          >
                            <StatusChip status={status} />
                            <span className="font-mono text-xs text-ink-500">{group.length}</span>
                          </button>
                        </td>
                      </tr>
                      {group.map((row) => <Row key={row.application_id} row={row} tz={tz} />)}
                    </tbody>
                  );
                })}
                {restStatuses.length ? (
                  <tbody>
                    <tr>
                      <td colSpan={cols.length} className="border-t border-cream-200 px-4 py-2 text-xs text-ink-500">
                        {t('pipeline.empty_rest')} · {restStatuses.map((s) => t(`status.${s}`)).join(' · ')}
                      </td>
                    </tr>
                  </tbody>
                ) : null}
              </table>
            </div>
          )}
        </>
      ) : null}
    </div>
  );
}
