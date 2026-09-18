import { ExternalLink } from 'lucide-react';
import { useState, type FormEvent } from 'react';
import { Link, useParams } from 'react-router-dom';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { Pill, SourceBadge, StatusChip } from '@/components/ui/Chips';
import { ConfirmCard } from '@/components/ui/ConfirmCard';
import { EmptyState } from '@/components/ui/EmptyState';
import { Field, inputClass } from '@/components/ui/Field';
import { PageHeader } from '@/components/ui/PageHeader';
import { PaperCard } from '@/components/ui/PaperCard';
import { useAddEvent, useApplication, useMeta, useSetStatus } from '@/hooks/useBoard';
import { fmtDateTime, nowLocalInput } from '@/lib/format';
import { useT } from '@/lib/i18n';
import type { ApplicationDetail, Status } from '@/lib/types';

const AUTO = '__auto__';
const REVIEW_THRESHOLD = 0.7;

function StatusEditor({ app, onDone }: { app: ApplicationDetail; onDone: () => void }) {
  const { t } = useT();
  const meta = useMeta();
  const setStatus = useSetStatus(app.application_id);
  const [target, setTarget] = useState<string>(app.user_status ?? AUTO);
  const [reason, setReason] = useState('');
  const after: Status = target === AUTO ? app.auto_status : (target as Status);

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-end gap-3">
        <Field label={t('application.change_status')}>
          <select className={inputClass} value={target} onChange={(e) => setTarget(e.target.value)}>
            <option value={AUTO}>{t('application.clear_status')} ({t(`status.${app.auto_status}`)})</option>
            {(meta.data?.statuses ?? []).map((s) => (
              <option key={s} value={s}>{t(`status.${s}`)}</option>
            ))}
          </select>
        </Field>
        {target === 'unsuitable' ? (
          <Field label={t('application.excluded_reason')}>
            <input className={inputClass} value={reason} onChange={(e) => setReason(e.target.value)} />
          </Field>
        ) : null}
      </div>
      {setStatus.isError ? <Alert tone="error">{setStatus.error.message}</Alert> : null}
      <ConfirmCard
        title={t('application.confirm.title')}
        before={<StatusChip status={app.status} />}
        after={<StatusChip status={after} />}
        hint={t('application.confirm.hint')}
        busy={setStatus.isPending}
        onCancel={onDone}
        onConfirm={() =>
          setStatus.mutate(
            { user_status: target === AUTO ? null : after, excluded_reason: target === 'unsuitable' && reason ? reason : null },
            { onSuccess: onDone },
          )
        }
      />
    </div>
  );
}

function EventForm({ app, onDone }: { app: ApplicationDetail; onDone: () => void }) {
  const { t } = useT();
  const meta = useMeta();
  const add = useAddEvent(app.application_id);
  const [type, setType] = useState('interview');
  const [when, setWhen] = useState(nowLocalInput);
  const [summary, setSummary] = useState('');
  const submit = (e: FormEvent) => {
    e.preventDefault();
    add.mutate(
      { event_type: type, occurred_at: new Date(when).toISOString(), summary: summary || null },
      { onSuccess: onDone },
    );
  };
  return (
    <form onSubmit={submit} className="grid gap-3 md:grid-cols-3">
      <Field label={t('application.events.type')}>
        <select className={inputClass} value={type} onChange={(e) => setType(e.target.value)}>
          {(meta.data?.event_types ?? []).map((et) => (
            <option key={et} value={et}>{t(`event.${et}` as never)}</option>
          ))}
        </select>
      </Field>
      <Field label={t('application.events.time')}>
        <input className={inputClass} type="datetime-local" required value={when} onChange={(e) => setWhen(e.target.value)} />
      </Field>
      <Field label={`${t('application.events.summary')} (${t('common.optional')})`}>
        <input className={inputClass} maxLength={120} value={summary} onChange={(e) => setSummary(e.target.value)} />
      </Field>
      {add.isError ? <div className="md:col-span-3"><Alert tone="error">{add.error.message}</Alert></div> : null}
      <div className="flex justify-end gap-2 md:col-span-3">
        <Button variant="ghost" onClick={onDone}>{t('common.cancel')}</Button>
        <Button type="submit" disabled={add.isPending}>{t('common.add')}</Button>
      </div>
    </form>
  );
}

export function ApplicationPage() {
  const { t, lang } = useT();
  const id = Number(useParams().id);
  const meta = useMeta();
  const q = useApplication(id);
  const [editing, setEditing] = useState(false);
  const [logging, setLogging] = useState(false);
  const [accepted, setAccepted] = useState<Set<number>>(new Set());
  const tz = meta.data?.tz ?? 'UTC';

  if (q.isError) return <EmptyState title={t('application.not_found')} action={<Link className="text-sm underline" to="/pipeline">{t('common.back')}</Link>} />;
  if (!q.data) return <p className="text-sm text-ink-500">{t('common.loading')}</p>;
  const app = q.data;

  return (
    <div className="space-y-5">
      <Link to="/pipeline" className="text-xs text-ink-500 hover:underline">← {t('nav.pipeline')}</Link>
      <PageHeader
        eyebrow={t('application.eyebrow')}
        title={app.company}
        hint={app.role ?? undefined}
        actions={
          app.job_url ? (
            <a href={app.job_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-sm text-ink-700 hover:underline">
              <ExternalLink size={14} /> {t('application.job_url')}
            </a>
          ) : null
        }
      />

      <PaperCard>
        <div className="flex flex-wrap items-center gap-3">
          <StatusChip status={app.status} autoStatus={app.auto_status} />
          <Pill>{t(`track.${app.track}`)}</Pill>
          <SourceBadge source="manual" />
          <span className="text-xs text-ink-500">
            {t('common.auto_status')}: {t(`status.${app.auto_status}`)}
          </span>
          <div className="ml-auto">
            {editing ? null : <Button size="sm" variant="outline" onClick={() => setEditing(true)}>{t('application.change_status')}</Button>}
          </div>
        </div>
        {editing ? <div className="mt-4"><StatusEditor app={app} onDone={() => setEditing(false)} /></div> : null}
        {app.excluded_reason ? <p className="mt-3 text-xs text-ink-500">{t('application.excluded_reason')}: {app.excluded_reason}</p> : null}
      </PaperCard>

      <div className="grid gap-4 lg:grid-cols-12">
        <div className="lg:col-span-8">
          <PaperCard>
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-ink-900">{t('application.events')}</h2>
              {logging ? null : <Button size="sm" onClick={() => setLogging(true)}>{t('application.events.add')}</Button>}
            </div>
            {logging ? <div className="mb-4"><EventForm app={app} onDone={() => setLogging(false)} /></div> : null}
            {app.events.length === 0 ? (
              <p className="text-sm text-ink-500">{t('application.events.empty')}</p>
            ) : (
              <ol className="divide-y divide-cream-200 text-sm">
                {[...app.events].reverse().map((e) => {
                  const needsReview = !e.user_confirmed && e.confidence < REVIEW_THRESHOLD && !accepted.has(e.event_id);
                  return (
                    <li key={e.event_id} className="py-2.5">
                      <div className="flex items-start gap-3">
                        <span className="w-52 shrink-0 font-mono text-xs text-ink-500">{fmtDateTime(e.occurred_at, tz, lang)}</span>
                        <div className="min-w-0 flex-1">
                          <div className="text-ink-900">{t(`event.${e.event_type}` as never)}</div>
                          {e.summary ? <div className="text-xs text-ink-500">{e.summary}</div> : null}
                        </div>
                        <SourceBadge source={e.source} />
                      </div>
                      {needsReview ? (
                        <div className="mt-1.5 ml-[14.5rem] flex flex-wrap items-center gap-2 text-xs">
                          <span
                            className="chip inline-flex items-center rounded-full border px-2 py-0.5 font-semibold"
                            style={{ color: 'var(--color-review-fg)', background: 'var(--color-review-bg)', borderColor: 'var(--color-review-border)' }}
                          >
                            {t('application.events.review_tag')}
                          </span>
                          <span className="text-ink-500">{t('application.events.confidence')}: {Math.round(e.confidence * 100)}%</span>
                          <Button size="sm" variant="ghost" onClick={() => setAccepted((s) => new Set(s).add(e.event_id))}>
                            {t('application.events.accept')}
                          </Button>
                          <Button size="sm" variant="ghost" onClick={() => setLogging(true)}>
                            {t('application.events.correct')}
                          </Button>
                        </div>
                      ) : (e.user_confirmed || accepted.has(e.event_id)) && e.confidence < REVIEW_THRESHOLD ? (
                        <div className="mt-1.5 ml-[14.5rem] text-xs text-ink-500">{t('application.events.confirmed_by_user')}</div>
                      ) : null}
                    </li>
                  );
                })}
              </ol>
            )}
          </PaperCard>
        </div>
        <div className="space-y-4 lg:col-span-4">
          <PaperCard>
            <h2 className="hand-body mb-2 text-lg text-ink-900">{t('application.notes')}</h2>
            <p className="whitespace-pre-wrap text-sm text-ink-700">{app.notes ?? t('common.none')}</p>
          </PaperCard>
          <PaperCard>
            <dl className="space-y-2 text-xs text-ink-700">
              <div className="flex justify-between gap-2"><dt className="text-ink-500">{t('application.applied_at')}</dt><dd className="font-mono">{app.applied_at ? fmtDateTime(app.applied_at, tz, lang) : t('common.none')}</dd></div>
              <div className="flex justify-between gap-2"><dt className="text-ink-500">{t('application.created_at')}</dt><dd className="font-mono">{fmtDateTime(app.created_at, tz, lang)}</dd></div>
            </dl>
          </PaperCard>
        </div>
      </div>
    </div>
  );
}
