import { ArrowUpRight, Plus } from 'lucide-react';
import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ApplicationForm } from '@/components/ApplicationForm';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { Pill, SourceBadge, StatusChip } from '@/components/ui/Chips';
import { EmptyState } from '@/components/ui/EmptyState';
import { Field, inputClass } from '@/components/ui/Field';
import { PageHeader } from '@/components/ui/PageHeader';
import { PaperCard } from '@/components/ui/PaperCard';
import { useApplications, useCreateApplication, useMeta } from '@/hooks/useBoard';
import { ApiError, apiMessage } from '@/lib/api';
import { useCampaign } from '@/lib/campaign';
import { daysAgo, fmtDateTime } from '@/lib/format';
import { useT } from '@/lib/i18n';
import { groupOf, STATUS_GROUPS, STATUS_ORDER, type StatusGroup } from '@/lib/status';
import { useToast } from '@/lib/toast';
import type { ApplicationRow } from '@/lib/types';

const ALL_TRACKS = 'all';
const ALL_GROUPS = 'all';
const GROUP_KEYS = Object.keys(STATUS_GROUPS) as StatusGroup[];
type GroupFilter = StatusGroup | typeof ALL_GROUPS;

function AddForm({ campaignId, onDone }: { campaignId: number; onDone: () => void }) {
  const { t } = useT();
  const meta = useMeta();
  const create = useCreateApplication();
  const navigate = useNavigate();
  const toast = useToast();

  const err = create.error;
  const duplicateId =
    err instanceof ApiError && err.code === 'application_exists' && typeof err.extra?.existing_application_id === 'number'
      ? err.extra.existing_application_id
      : null;

  return (
    <PaperCard>
      <ApplicationForm
        mode="add"
        tz={meta.data?.tz ?? 'UTC'}
        tracks={meta.data?.tracks ?? []}
        statuses={meta.data?.statuses ?? []}
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
                onDone();
                toast.show(t('toast.application_added'));
                navigate(`/pipeline/${detail.application_id}`);
              },
            },
          )
        }
        onCancel={onDone}
      />
    </PaperCard>
  );
}

function Row({ row, tz }: { row: ApplicationRow; tz: string }) {
  const { t, lang } = useT();
  const next = row.deadline_at ?? row.next_action_due;
  return (
    <tr className={row.is_ghosted ? 'ghosted' : ''}>
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
            {t(`event.${row.last_event_type}` as never)}
            {row.last_event_at ? <div className="font-mono text-[11px] text-ink-500">{fmtDateTime(row.last_event_at, tz, lang)}</div> : null}
          </>
        ) : t('common.none')}
      </td>
      <td className="px-4 py-3 font-mono text-xs text-ink-700">
        {next ? fmtDateTime(next, tz, lang) : t('common.none')}
        {row.next_action ? <div className="font-sans text-[11px] text-ink-500">{row.next_action}</div> : null}
      </td>
      <td className="px-4 py-3"><SourceBadge source="manual" /></td>
      <td className="px-4 py-3">
        <Link
          to={`/pipeline/${row.application_id}`}
          aria-label={t('common.open')}
          title={t('common.open')}
          className="inline-flex h-7 w-7 items-center justify-center rounded-lg text-ink-500 hover:bg-cream-100"
        >
          <ArrowUpRight size={14} />
        </Link>
      </td>
    </tr>
  );
}

export function PipelinePage() {
  const { t } = useT();
  const { current, loaded } = useCampaign();
  const meta = useMeta();
  const apps = useApplications(current?.campaign_id ?? null);
  const [adding, setAdding] = useState(false);
  const [track, setTrack] = useState<string>(ALL_TRACKS);
  const [keyword, setKeyword] = useState('');
  const [activeGroup, setActiveGroup] = useState<GroupFilter>(ALL_GROUPS);
  const tz = meta.data?.tz ?? 'UTC';

  if (loaded && !current) {
    return <EmptyState title={t('settings.campaigns.empty')} action={<Link className="text-sm underline" to="/settings">{t('nav.settings')}</Link>} />;
  }
  const rows = apps.data ?? [];
  const cols: string[] = ['company', 'role', 'status', 'last_event', 'next', 'source', 'open'];
  const keywordLower = keyword.trim().toLowerCase();
  const filteredRows = rows.filter(
    (r) =>
      (activeGroup === ALL_GROUPS || groupOf(r.status) === activeGroup) &&
      (track === ALL_TRACKS || r.track === track) &&
      (!keywordLower || `${r.company} ${r.role ?? ''}`.toLowerCase().includes(keywordLower)),
  );
  const clearFilters = () => { setTrack(ALL_TRACKS); setKeyword(''); setActiveGroup(ALL_GROUPS); };
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
      {adding && current ? <AddForm campaignId={current.campaign_id} onDone={() => setAdding(false)} /> : null}
      {apps.isLoading ? <p className="text-sm text-ink-500">{t('common.loading')}</p> : null}
      {apps.isError ? (
        <Alert tone="error">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span>{t('common.error', { message: apps.error.message })}</span>
            <Button variant="outline" size="sm" onClick={() => apps.refetch()}>{t('common.retry')}</Button>
          </div>
        </Alert>
      ) : null}
      {apps.isSuccess && rows.length === 0 ? (
        <EmptyState title={t('pipeline.empty')} />
      ) : apps.isSuccess ? (
        <>
          <div role="group" aria-label={t('pipeline.col.status')} className="inline-flex rounded-full border border-cream-200 bg-cream-100 p-1 text-sm">
            {([ALL_GROUPS, ...GROUP_KEYS] as GroupFilter[]).map((g) => {
              const count = g === ALL_GROUPS ? rows.length : rows.filter((r) => groupOf(r.status) === g).length;
              return (
                <button
                  key={g}
                  type="button"
                  aria-pressed={activeGroup === g}
                  onClick={() => setActiveGroup(g)}
                  className={[
                    'inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 font-medium transition-colors',
                    activeGroup === g ? 'bg-cream-300 text-ink-900' : 'text-ink-500 hover:text-ink-700',
                  ].join(' ')}
                >
                  {g === ALL_GROUPS ? t('pipeline.filter.all') : t(`group.${g}`)}
                  <span className="font-mono text-[11px] text-ink-500">{count}</span>
                </button>
              );
            })}
          </div>
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
                    {cols.map((c) =>
                      c === 'open' ? (
                        <th key={c} className="px-4 py-2 font-semibold" aria-label={t('common.open')} />
                      ) : (
                        <th key={c} className="px-4 py-2 font-semibold">{t(`pipeline.col.${c}` as never)}</th>
                      ),
                    )}
                  </tr>
                </thead>
                {STATUS_ORDER.map((status) => {
                  const group = filteredRows.filter((r) => r.status === status);
                  if (group.length === 0) return null;
                  return (
                    <tbody key={status} className="divide-y divide-cream-200 border-t border-cream-200">
                      <tr className="bg-cream-50/60">
                        <td colSpan={cols.length} className="px-4 py-1.5">
                          <span className="inline-flex items-center gap-2"><StatusChip status={status} /><span className="font-mono text-xs text-ink-500">{group.length}</span></span>
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
