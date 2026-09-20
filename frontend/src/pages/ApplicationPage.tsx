import {
  Award,
  Bell,
  CalendarClock,
  Check,
  CheckCircle2,
  Circle,
  ClipboardCheck,
  ExternalLink,
  FileText,
  StickyNote,
  Users,
  XCircle,
} from 'lucide-react';
import { useState, type FormEvent } from 'react';
import { Link, useParams } from 'react-router-dom';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { Pill, SourceBadge, StatusChip } from '@/components/ui/Chips';
import { ConfirmCard } from '@/components/ui/ConfirmCard';
import { EmptyState } from '@/components/ui/EmptyState';
import { Field, inputClass } from '@/components/ui/Field';
import { PaperCard } from '@/components/ui/PaperCard';
import { useAddEvent, useApplication, useMeta, useSetStatus } from '@/hooks/useBoard';
import { useCampaign } from '@/lib/campaign';
import { fmtDate, fmtDateTime, nowLocalInput } from '@/lib/format';
import { useT } from '@/lib/i18n';
import type { ApplicationDetail, Status } from '@/lib/types';

const AUTO = '__auto__';
const REVIEW_THRESHOLD = 0.7;

const EVENT_ICON: Record<string, typeof Circle> = {
  interview: Users,
  final_interview: Users,
  casual_interview: Users,
  entry: FileText,
  es_submitted: FileText,
  document_screening: FileText,
  ack: FileText,
  viewed: FileText,
  assessment: ClipboardCheck,
  web_test: ClipboardCheck,
  scheduling: CalendarClock,
  pass: CheckCircle2,
  offer: Award,
  offer_informal: Award,
  offer_meeting: Award,
  accepted: Award,
  joined: Award,
  rejection: XCircle,
  withdrawn: XCircle,
  portal_check_required: ExternalLink,
  followup_needed: Bell,
  note: StickyNote,
};

function StatusEditor({
  app,
  onCancel,
  onConfirmed,
}: {
  app: ApplicationDetail;
  onCancel: () => void;
  onConfirmed: () => void;
}) {
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
        title={`${t('application.confirm.change_to')} ${t(`status.${after}`)}`}
        eyebrow={t('application.confirm.eyebrow')}
        badge={<SourceBadge source="manual" />}
        before={<StatusChip status={app.status} />}
        after={<StatusChip status={after} />}
        hint={t('application.confirm.hint')}
        busy={setStatus.isPending}
        onCancel={onCancel}
        onConfirm={() =>
          setStatus.mutate(
            { user_status: target === AUTO ? null : after, excluded_reason: target === 'unsuitable' && reason ? reason : null },
            { onSuccess: onConfirmed },
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
      <div className="flex items-center gap-2 text-xs text-ink-500 md:col-span-3">
        <SourceBadge source="manual" /> {t('common.source_note')}
      </div>
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
  const { campaigns, current, select } = useCampaign();
  const addNote = useAddEvent(id);
  const [editing, setEditing] = useState(false);
  const [logging, setLogging] = useState(false);
  const [accepted, setAccepted] = useState<Set<number>>(new Set());
  const [confirmedAt, setConfirmedAt] = useState<string | null>(null);
  const [noteText, setNoteText] = useState('');
  const tz = meta.data?.tz ?? 'UTC';

  if (q.isError) return <EmptyState title={t('application.not_found')} action={<Link className="text-sm underline" to="/pipeline">{t('common.back')}</Link>} />;
  if (!q.data) return <p className="text-sm text-ink-500">{t('common.loading')}</p>;
  const app = q.data;

  const breadcrumb = (
    <nav aria-label="breadcrumb" className="text-xs text-ink-500">
      <Link to="/pipeline" className="hover:underline">{t('nav.pipeline')}</Link>
      <span className="mx-1">›</span>
      <span className="text-ink-700">{app.company}{app.role ? ` · ${app.role}` : ''}</span>
    </nav>
  );

  if (current && app.campaign_id !== current.campaign_id) {
    const owner = campaigns.find((c) => c.campaign_id === app.campaign_id);
    return (
      <div className="space-y-5">
        {breadcrumb}
        <EmptyState
          title={`${t('application.belongs_to')} ${owner?.name ?? ''}`}
          action={
            owner ? (
              <Button size="sm" variant="outline" onClick={() => select(app.campaign_id)}>
                {t('application.switch_to')} {owner.name}
              </Button>
            ) : undefined
          }
        />
      </div>
    );
  }

  const campaignName = campaigns.find((c) => c.campaign_id === app.campaign_id)?.name ?? '';
  const latest = app.events.length
    ? app.events.reduce((a, b) => (a.occurred_at > b.occurred_at ? a : b))
    : null;
  const portalUrl = app.portal_url ?? app.job_url;

  return (
    <div className="space-y-5">
      {breadcrumb}

      <PaperCard>
        <div className="grid gap-4 md:grid-cols-[1.6fr_1fr]">
          <div className="min-w-0">
            <div className="text-[11px] font-semibold uppercase tracking-[0.12em] text-ink-500">
              {t('application.eyebrow')} · {campaignName}
            </div>
            <h1 className="serif mt-0.5 text-3xl font-medium tracking-tight text-ink-900">{app.company}</h1>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              {app.role ? <span className="text-sm text-ink-700">{app.role}</span> : null}
              <Pill>{t(`track.${app.track}`)}</Pill>
            </div>
            <div className="mt-3">
              <SourceBadge source="manual" />
            </div>
          </div>
          <div className="flex flex-col items-start gap-2 md:items-end">
            <div className="flex flex-wrap items-center gap-2">
              <StatusChip status={app.status} autoStatus={app.auto_status} />
              {editing ? null : (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    setEditing(true);
                    setConfirmedAt(null);
                  }}
                >
                  {t('application.change_status')}
                </Button>
              )}
            </div>
            {!editing && confirmedAt ? (
              <div
                role="status"
                className="inline-flex items-center gap-2 rounded-lg px-3 py-1.5 text-xs"
                style={{ background: 'var(--color-pos-50)', color: 'var(--color-pos-500)' }}
              >
                <Check size={14} /> {t('application.confirm.done')} · <span className="font-mono">{fmtDateTime(confirmedAt, tz, lang)}</span>
              </div>
            ) : null}
            <div className="text-xs text-ink-500 md:text-right">
              <div>{t('common.user_status')}: {app.user_status ? t(`status.${app.user_status}`) : t('common.none')}</div>
              <div>
                {t('common.auto_status')}: {t(`status.${app.auto_status}`)}
                {latest ? (
                  <>
                    {' '}· {t('common.derived_from')} {t(`event.${latest.event_type}` as never)}{' '}
                    <span className="font-mono">{fmtDate(latest.occurred_at, tz, lang)}</span>
                  </>
                ) : null}
              </div>
            </div>
            {portalUrl ? (
              <a
                href={portalUrl}
                target="_blank"
                rel="noreferrer"
                className="inline-flex h-8 items-center justify-center gap-2 rounded-lg border border-ink-200 bg-transparent px-3 text-xs font-medium text-ink-900 transition-colors hover:bg-cream-100"
              >
                <ExternalLink size={14} /> {t('common.open_portal')}
              </a>
            ) : null}
          </div>
        </div>
        {editing ? (
          <div className="mt-4">
            <StatusEditor
              app={app}
              onCancel={() => setEditing(false)}
              onConfirmed={() => {
                setEditing(false);
                setConfirmedAt(new Date().toISOString());
              }}
            />
          </div>
        ) : null}
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
              <ol className="relative ml-3 space-y-4 border-l border-dashed border-cream-400 pl-6 text-sm">
                {[...app.events].reverse().map((e) => {
                  const Icon = EVENT_ICON[e.event_type] ?? Circle;
                  const needsReview = !e.user_confirmed && e.confidence < REVIEW_THRESHOLD && !accepted.has(e.event_id);
                  return (
                    <li key={e.event_id} className="relative">
                      <span
                        aria-hidden
                        className="absolute -left-[37px] top-0.5 flex h-6 w-6 items-center justify-center rounded-full border border-ink-200 bg-cream-50 text-ink-700"
                      >
                        <Icon size={12} />
                      </span>
                      <div className="flex items-start gap-3">
                        <span className="w-52 shrink-0 font-mono text-xs text-ink-500">{fmtDateTime(e.occurred_at, tz, lang)}</span>
                        <div className="min-w-0 flex-1">
                          <div className="text-ink-900">{t(`event.${e.event_type}` as never)}</div>
                          {e.summary ? <div className="text-xs text-ink-500">{e.summary}</div> : null}
                        </div>
                        <SourceBadge source={e.source} />
                      </div>
                      {needsReview ? (
                        <div className="mt-1.5 flex flex-wrap items-center gap-2 text-xs">
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
                        <div className="mt-1.5 text-xs text-ink-500">{t('application.events.confirmed_by_user')}</div>
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
            {app.notes ? <p className="whitespace-pre-wrap text-sm text-ink-700">{app.notes}</p> : null}
            {addNote.isError ? <div className="mt-2"><Alert tone="error">{addNote.error.message}</Alert></div> : null}
            <textarea
              className={`${inputClass} hand-body mt-2 resize-y text-[15px] leading-[1.75]`}
              rows={3}
              placeholder={t('application.notes.placeholder')}
              value={noteText}
              onChange={(e) => setNoteText(e.target.value)}
            />
            <div className="mt-2 flex justify-end">
              <Button
                size="sm"
                disabled={!noteText.trim() || addNote.isPending}
                onClick={() =>
                  addNote.mutate(
                    { event_type: 'note', occurred_at: new Date().toISOString(), summary: noteText.trim() },
                    { onSuccess: () => setNoteText('') },
                  )
                }
              >
                {t('application.notes.save_as_event')}
              </Button>
            </div>
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
