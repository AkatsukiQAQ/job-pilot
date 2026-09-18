import { Plus } from 'lucide-react';
import { useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { SourceBadge, StatusChip } from '@/components/ui/Chips';
import { EmptyState } from '@/components/ui/EmptyState';
import { Field, inputClass } from '@/components/ui/Field';
import { PageHeader } from '@/components/ui/PageHeader';
import { PaperCard } from '@/components/ui/PaperCard';
import { useApplications, useCreateApplication, useMeta } from '@/hooks/useBoard';
import { useCampaign } from '@/lib/campaign';
import { daysAgo, fmtDateTime } from '@/lib/format';
import { useT } from '@/lib/i18n';
import { STATUS_ORDER } from '@/lib/status';
import type { ApplicationRow, Track } from '@/lib/types';

function AddForm({ campaignId, onDone }: { campaignId: number; onDone: () => void }) {
  const { t } = useT();
  const meta = useMeta();
  const create = useCreateApplication();
  const navigate = useNavigate();
  const [form, setForm] = useState({ company_name: '', role: '', track: 'newgrad' as Track, job_url: '', notes: '' });
  const set = (k: keyof typeof form) => (e: { target: { value: string } }) => setForm({ ...form, [k]: e.target.value });

  const submit = (e: FormEvent) => {
    e.preventDefault();
    create.mutate(
      {
        campaign_id: campaignId,
        company_name: form.company_name,
        role: form.role || null,
        track: form.track,
        job_url: form.job_url || null,
        notes: form.notes || null,
      },
      { onSuccess: (detail) => { onDone(); navigate(`/pipeline/${detail.application_id}`); } },
    );
  };

  return (
    <PaperCard>
      <form onSubmit={submit} className="grid gap-4 md:grid-cols-2">
        <Field label={t('pipeline.form.company')}>
          <input className={inputClass} required value={form.company_name} onChange={set('company_name')} />
        </Field>
        <Field label={`${t('pipeline.form.role')} (${t('common.optional')})`}>
          <input className={inputClass} value={form.role} onChange={set('role')} />
        </Field>
        <Field label={t('pipeline.form.track')}>
          <select className={inputClass} value={form.track} onChange={set('track')}>
            {(meta.data?.tracks ?? []).map((tr) => (
              <option key={tr} value={tr}>{t(`track.${tr}`)}</option>
            ))}
          </select>
        </Field>
        <Field label={`${t('pipeline.form.job_url')} (${t('common.optional')})`}>
          <input className={inputClass} type="url" value={form.job_url} onChange={set('job_url')} />
        </Field>
        <div className="md:col-span-2">
          <Field label={`${t('pipeline.form.notes')} (${t('common.optional')})`}>
            <textarea className={inputClass} rows={2} value={form.notes} onChange={set('notes')} />
          </Field>
        </div>
        {create.isError ? (
          <div className="md:col-span-2"><Alert tone="error">{create.error.message}</Alert></div>
        ) : null}
        <div className="flex justify-end gap-2 md:col-span-2">
          <Button variant="ghost" onClick={onDone}>{t('common.cancel')}</Button>
          <Button type="submit" disabled={create.isPending}>{t('common.add')}</Button>
        </div>
      </form>
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
      <td className="px-4 py-3 text-ink-700">{row.role ?? t('common.none')}</td>
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
    </tr>
  );
}

export function PipelinePage() {
  const { t } = useT();
  const { current, loaded } = useCampaign();
  const meta = useMeta();
  const apps = useApplications(current?.campaign_id ?? null);
  const [adding, setAdding] = useState(false);
  const tz = meta.data?.tz ?? 'UTC';

  if (loaded && !current) {
    return <EmptyState title={t('settings.campaigns.empty')} action={<Link className="text-sm underline" to="/settings">{t('nav.settings')}</Link>} />;
  }
  const rows = apps.data ?? [];
  const cols: string[] = ['company', 'role', 'status', 'last_event', 'next', 'source'];

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow={t('pipeline.eyebrow')}
        title={t('pipeline.title')}
        hint={current?.name}
        actions={
          <Button onClick={() => setAdding(true)} leadingIcon={<Plus size={16} />} disabled={!current}>
            {t('pipeline.add')}
          </Button>
        }
      />
      {adding && current ? <AddForm campaignId={current.campaign_id} onDone={() => setAdding(false)} /> : null}
      {apps.isError ? <Alert tone="error">{t('common.error', { message: apps.error.message })}</Alert> : null}
      {apps.isSuccess && rows.length === 0 ? (
        <EmptyState title={t('pipeline.empty')} />
      ) : (
        <div className="overflow-hidden rounded-2xl border border-cream-200 bg-cream-100">
          <table className="w-full text-sm">
            <thead className="bg-cream-200/60 text-left text-xs uppercase tracking-wide text-ink-500">
              <tr>{cols.map((c) => <th key={c} className="px-4 py-2 font-semibold">{t(`pipeline.col.${c}` as never)}</th>)}</tr>
            </thead>
            {STATUS_ORDER.map((status) => {
              const group = rows.filter((r) => r.status === status);
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
          </table>
        </div>
      )}
    </div>
  );
}
