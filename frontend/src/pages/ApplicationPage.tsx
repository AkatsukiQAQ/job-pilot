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
  Trash2,
  Users,
  XCircle,
} from 'lucide-react';
import { useState, type FormEvent, type ReactNode } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { ApplicationForm } from '@/components/ApplicationForm';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { Pill, SourceBadge, StatusChip } from '@/components/ui/Chips';
import { ConfirmCard } from '@/components/ui/ConfirmCard';
import { EmptyState } from '@/components/ui/EmptyState';
import { Field, inputClass } from '@/components/ui/Field';
import { PaperCard } from '@/components/ui/PaperCard';
import {
  useAddEvent,
  useApplication,
  useDeleteApplication,
  useDeleteEvent,
  useMeta,
  useSetStatus,
  useUpdateApplication,
  useUpdateEvent,
} from '@/hooks/useBoard';
import { ApiError, apiMessage } from '@/lib/api';
import { useCampaign } from '@/lib/campaign';
import { fmtDate, fmtDateTime, isoToZonedInput, nowInputInTz, zonedInputToIso } from '@/lib/format';
import { useT } from '@/lib/i18n';
import { STATUS_ORDER } from '@/lib/status';
import { useToast } from '@/lib/toast';
import type { ApplicationDetail, EventIn, EventOut, EventType, Status } from '@/lib/types';

const AUTO = '__auto__';
const REVIEW_THRESHOLD = 0.7;

const EVENT_ICON: Partial<Record<EventType, typeof Circle>> = {
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
  const [reason, setReason] = useState(app.excluded_reason ?? '');
  const after: Status = target === AUTO ? app.auto_status : (target as Status);

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-end gap-3">
        <Field label={t('application.change_status')}>
          <select className={inputClass} value={target} onChange={(e) => setTarget(e.target.value)}>
            <option value={AUTO}>{t('application.clear_status')} ({t(`status.${app.auto_status}`)})</option>
            {(meta.data?.statuses ?? []).filter((s) => s !== 'unrecorded').map((s) => (
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
      {setStatus.isError ? <Alert tone="error">{apiMessage(t, setStatus.error)}</Alert> : null}
      <ConfirmCard
        title={`${t('application.confirm.change_to')} ${t(`status.${after}`)}`}
        before={<StatusChip status={app.status} />}
        after={<StatusChip status={after} />}
        hint={t('application.confirm.hint')}
        busy={setStatus.isPending}
        onCancel={() => {
          setStatus.reset();
          onCancel();
        }}
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

function EventForm({
  initial,
  tz,
  busy,
  error,
  onSubmit,
  onCancel,
}: {
  initial?: EventOut;
  tz: string;
  busy?: boolean;
  error?: ReactNode;
  onSubmit: (body: EventIn) => void;
  onCancel: () => void;
}) {
  const { t } = useT();
  const meta = useMeta();
  const [type, setType] = useState<EventType | ''>(initial?.event_type ?? meta.data?.event_types[0] ?? '');
  const [when, setWhen] = useState(() => (initial ? isoToZonedInput(initial.occurred_at, tz) : nowInputInTz(tz)));
  const [summary, setSummary] = useState(initial?.summary ?? '');
  const [invalid, setInvalid] = useState(false);
  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (!type || !when) {
      setInvalid(true);
      return;
    }
    setInvalid(false);
    onSubmit({ event_type: type, occurred_at: zonedInputToIso(when, tz), summary: summary.trim() || null });
  };
  return (
    <form onSubmit={submit} className="grid gap-3 md:grid-cols-3">
      <Field label={t('application.events.type')}>
        <select className={inputClass} value={type} onChange={(e) => setType(e.target.value as EventType)}>
          {(meta.data?.event_types ?? []).map((et) => (
            <option key={et} value={et}>{t(`event.${et}`)}</option>
          ))}
        </select>
      </Field>
      <Field label={t('application.events.time')}>
        <input className={inputClass} type="datetime-local" value={when} onChange={(e) => setWhen(e.target.value)} />
        <p className="mt-1 text-xs text-ink-500">{t('time.tz_hint', { tz })}</p>
      </Field>
      <Field label={`${t('application.events.summary')} (${t('common.optional')})`}>
        <input className={inputClass} maxLength={120} value={summary} onChange={(e) => setSummary(e.target.value)} />
      </Field>
      {invalid ? <div className="md:col-span-3"><Alert tone="error">{t('api.validation_failed')}</Alert></div> : null}
      {error ? <div className="md:col-span-3">{error}</div> : null}
      <div className="flex items-center gap-2 text-xs text-ink-500 md:col-span-3">
        <SourceBadge source="manual" /> {t('common.source_note')}
      </div>
      <div className="flex justify-end gap-2 md:col-span-3">
        <Button variant="ghost" onClick={onCancel}>{t('common.cancel')}</Button>
        <Button type="submit" disabled={busy}>{initial ? t('common.save') : t('common.add')}</Button>
      </div>
    </form>
  );
}

export function ApplicationPage() {
  const { t, lang } = useT();
  const id = Number(useParams().id);
  const validId = Number.isInteger(id);
  const navigate = useNavigate();
  const meta = useMeta();
  const q = useApplication(id);
  const { campaigns, current, select, loaded } = useCampaign();
  const addNote = useAddEvent(id);
  const addEvent = useAddEvent(id);
  const updateEvent = useUpdateEvent(id);
  const setStatus = useSetStatus(id);
  const toast = useToast();
  const update = useUpdateApplication(id);
  const del = useDeleteApplication(id);
  const delEvent = useDeleteEvent(id);
  const [editing, setEditing] = useState(false);
  const [editingFields, setEditingFields] = useState(false);
  const [logging, setLogging] = useState(false);
  const [accepted, setAccepted] = useState<Set<number>>(new Set());
  const [confirmedAt, setConfirmedAt] = useState<string | null>(null);
  const [noteText, setNoteText] = useState('');
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [deletingEventId, setDeletingEventId] = useState<number | null>(null);
  const [editingEventId, setEditingEventId] = useState<number | null>(null);
  const tz = current?.tz ?? meta.data?.tz ?? 'UTC';
  const ready = Boolean(meta.data) && loaded;

  const notFound = (
    <EmptyState title={t('application.not_found')} action={<Link className="text-sm underline" to="/pipeline">{t('common.back')}</Link>} />
  );
  if (!validId) return notFound;
  if (q.isError) {
    const status = q.error instanceof ApiError ? q.error.status : undefined;
    if (status === 404) return notFound;
    return (
      <div className="space-y-3">
        <Alert tone="error">{apiMessage(t, q.error)}</Alert>
        <Button variant="outline" size="sm" onClick={() => q.refetch()}>{t('common.retry')}</Button>
      </div>
    );
  }
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
                {t('application.switch_to', { name: owner.name })}
              </Button>
            ) : undefined
          }
        />
      </div>
    );
  }

  const campaignName = campaigns.find((c) => c.campaign_id === app.campaign_id)?.name ?? '';
  const portalUrl = app.portal_url ?? app.job_url;
  const portalIsHttp = portalUrl !== null && /^https?:\/\//i.test(portalUrl);
  const statusAdvanced =
    app.user_status !== null && STATUS_ORDER.indexOf(app.auto_status) > STATUS_ORDER.indexOf(app.user_status);
  const existingId =
    update.error instanceof ApiError && update.error.code === 'application_exists'
      ? update.error.extra?.existing_application_id
      : undefined;

  const toggleEvent = (eventId: number) => {
    updateEvent.reset();
    delEvent.reset();
    setDeletingEventId(null);
    setEditingEventId((prev) => (prev === eventId ? null : eventId));
  };

  return (
    <div className="space-y-5">
      {breadcrumb}

      <PaperCard>
        <div className="grid gap-4 md:grid-cols-[1.6fr_1fr]">
          {editingFields ? (
            <ApplicationForm
              mode="edit"
              initial={app}
              tz={tz}
              tracks={meta.data?.tracks ?? []}
              statuses={meta.data?.statuses ?? []}
              busy={update.isPending}
              error={
                update.isError ? (
                  <Alert tone="error">
                    {apiMessage(t, update.error)}
                    {typeof existingId === 'number' ? (
                      <>
                        {' '}·{' '}
                        <Link className="underline" to={`/pipeline/${existingId}`}>{t('application.duplicate.view_existing')}</Link>
                      </>
                    ) : null}
                  </Alert>
                ) : undefined
              }
              onSubmit={(v) =>
                update.mutate(v, {
                  onSuccess: () => {
                    setEditingFields(false);
                    toast.show(t('toast.application_updated'));
                  },
                })
              }
              onCancel={() => {
                update.reset();
                setEditingFields(false);
              }}
            />
          ) : (
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
          )}
          <div className="flex flex-col items-start gap-2 md:items-end">
            <div className="flex flex-wrap items-center gap-2">
              <StatusChip status={app.status} autoStatus={app.auto_status} />
              {editing || editingFields ? null : (
                <>
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={!ready}
                    onClick={() => {
                      setEditing(true);
                      setConfirmedAt(null);
                    }}
                  >
                    {t('application.change_status')}
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={!ready}
                    onClick={() => {
                      update.reset();
                      setEditingFields(true);
                    }}
                  >
                    {t('common.edit')}
                  </Button>
                </>
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
                {app.last_event_type && app.last_event_at ? (
                  <>
                    {' '}· {t('common.derived_from', { event: t(`event.${app.last_event_type}`) })}{' '}
                    <span className="font-mono">{fmtDate(app.last_event_at, tz, lang)}</span>
                  </>
                ) : null}
              </div>
            </div>
            {portalUrl ? (
              portalIsHttp ? (
                <a
                  href={portalUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex h-8 items-center justify-center gap-2 rounded-lg border border-ink-200 bg-transparent px-3 text-xs font-medium text-ink-900 transition-colors hover:bg-cream-100"
                >
                  <ExternalLink size={14} /> {t('common.open_portal')}
                </a>
              ) : (
                <span className="break-all font-mono text-xs text-ink-500">{portalUrl}</span>
              )
            ) : null}
          </div>
        </div>
        {statusAdvanced ? (
          <div className="mt-4">
            <Alert tone="warning">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span>{t('application.status_advanced', { status: t(`status.${app.auto_status}`) })}</span>
                <Button size="sm" variant="outline" disabled={setStatus.isPending} onClick={() => setStatus.mutate({ user_status: null })}>
                  {t('application.clear_status')}
                </Button>
              </div>
            </Alert>
            {setStatus.isError ? <div className="mt-2"><Alert tone="error">{apiMessage(t, setStatus.error)}</Alert></div> : null}
          </div>
        ) : null}
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
              {logging ? null : (
                <Button size="sm" disabled={!ready} onClick={() => setLogging(true)}>{t('application.events.add')}</Button>
              )}
            </div>
            {logging ? (
              <div className="mb-4">
                <EventForm
                  tz={tz}
                  busy={addEvent.isPending}
                  error={addEvent.isError ? <Alert tone="error">{apiMessage(t, addEvent.error)}</Alert> : undefined}
                  onSubmit={(body) =>
                    addEvent.mutate(body, {
                      onSuccess: () => {
                        setLogging(false);
                        toast.show(t('toast.event_logged'));
                      },
                    })
                  }
                  onCancel={() => {
                    addEvent.reset();
                    setLogging(false);
                  }}
                />
              </div>
            ) : null}
            {app.events.length === 0 ? (
              <p className="text-sm text-ink-500">{t('application.events.empty')}</p>
            ) : (
              <ol className="relative ml-3 space-y-2 border-l border-dashed border-cream-400 pl-6 text-sm">
                {[...app.events].reverse().map((e) => {
                  const Icon = EVENT_ICON[e.event_type] ?? Circle;
                  const needsReview = !e.user_confirmed && e.confidence < REVIEW_THRESHOLD && !accepted.has(e.event_id);
                  const expanded = editingEventId === e.event_id;
                  return (
                    <li key={e.event_id} className="relative">
                      <span
                        aria-hidden
                        className="absolute -left-[37px] top-2.5 flex h-6 w-6 items-center justify-center rounded-full border border-ink-200 bg-cream-50 text-ink-700"
                      >
                        <Icon size={12} />
                      </span>
                      <div
                        role="button"
                        tabIndex={0}
                        aria-expanded={expanded}
                        aria-label={t('application.events.edit')}
                        className="-mx-3 cursor-pointer rounded-xl px-3 py-2 transition-colors hover:bg-cream-100 focus-visible:outline-2 focus-visible:outline-cream-500"
                        onClick={() => toggleEvent(e.event_id)}
                        onKeyDown={(ev) => {
                          if (ev.target !== ev.currentTarget) return;
                          if (ev.key === 'Enter' || ev.key === ' ') {
                            ev.preventDefault();
                            toggleEvent(e.event_id);
                          }
                        }}
                      >
                        <div className="flex items-start gap-3">
                          <span className="w-52 shrink-0 font-mono text-xs text-ink-500">{fmtDateTime(e.occurred_at, tz, lang)}</span>
                          <div className="min-w-0 flex-1">
                            <div className="text-ink-900">{t(`event.${e.event_type}`)}</div>
                            {e.summary ? <div className="text-xs text-ink-500">{e.summary}</div> : null}
                          </div>
                          <SourceBadge source={e.source} />
                        </div>
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
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={(ev) => {
                                ev.stopPropagation();
                                setAccepted((s) => new Set(s).add(e.event_id));
                              }}
                            >
                              {t('application.events.accept')}
                            </Button>
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={(ev) => {
                                ev.stopPropagation();
                                if (!expanded) toggleEvent(e.event_id);
                              }}
                            >
                              {t('application.events.correct')}
                            </Button>
                          </div>
                        ) : (e.user_confirmed || accepted.has(e.event_id)) && e.confidence < REVIEW_THRESHOLD ? (
                          <div className="mt-1.5 text-xs text-ink-500">{t('application.events.confirmed_by_user')}</div>
                        ) : null}
                      {expanded ? (
                        <div className="mt-2 space-y-3">
                          <EventForm
                            initial={e}
                            tz={tz}
                            busy={updateEvent.isPending}
                            error={updateEvent.isError ? <Alert tone="error">{apiMessage(t, updateEvent.error)}</Alert> : undefined}
                            onSubmit={(body) =>
                              updateEvent.mutate(
                                { eventId: e.event_id, body },
                                {
                                  onSuccess: () => {
                                    setEditingEventId(null);
                                    toast.show(t('toast.event_updated'));
                                  },
                                },
                              )
                            }
                            onCancel={() => {
                              updateEvent.reset();
                              setEditingEventId(null);
                            }}
                          />
                          {deletingEventId === e.event_id ? (
                            <div>
                              <ConfirmCard
                                title={t('application.events.delete_title')}
                                hint={t('application.events.delete_hint')}
                                confirmVariant="danger"
                                confirmLabel={t('common.delete')}
                                busy={delEvent.isPending}
                                onCancel={() => {
                                  delEvent.reset();
                                  setDeletingEventId(null);
                                }}
                                onConfirm={() =>
                                  delEvent.mutate(e.event_id, {
                                    onSuccess: () => {
                                      setDeletingEventId(null);
                                      setEditingEventId(null);
                                      toast.show(t('toast.event_deleted'));
                                    },
                                  })
                                }
                              />
                              {delEvent.isError ? <div className="mt-2"><Alert tone="error">{apiMessage(t, delEvent.error)}</Alert></div> : null}
                            </div>
                          ) : (
                            <Button
                              variant="ghost"
                              size="sm"
                              className="text-neg-500"
                              leadingIcon={<Trash2 size={14} />}
                              onClick={(ev) => {
                                ev.stopPropagation();
                                setDeletingEventId(e.event_id);
                              }}
                            >
                              {t('common.delete')}
                            </Button>
                          )}
                        </div>
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
            {addNote.isError ? <div className="mt-2"><Alert tone="error">{apiMessage(t, addNote.error)}</Alert></div> : null}
            <textarea
              className={`${inputClass} hand-body mt-2 resize-y text-[15px] leading-[1.75]`}
              rows={3}
              maxLength={120}
              placeholder={t('application.notes.placeholder')}
              value={noteText}
              onChange={(e) => setNoteText(e.target.value)}
            />
            <div className="mt-1 flex items-center justify-between">
              <span className="text-[11px] text-ink-500">{t('common.chars_left', { n: 120 - noteText.length })}</span>
              <Button
                size="sm"
                disabled={!noteText.trim() || addNote.isPending}
                onClick={() =>
                  addNote.mutate(
                    { event_type: 'note', occurred_at: new Date().toISOString(), summary: noteText.trim() },
                    {
                      onSuccess: () => {
                        setNoteText('');
                        toast.show(t('toast.note_saved'));
                      },
                    },
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

      <PaperCard>
        <h2 className="text-sm font-semibold text-ink-900">{t('application.delete.zone')}</h2>
        <p className="mt-1 text-xs text-ink-500">{t('application.delete.hint', { n: app.events.length })}</p>
        {confirmingDelete ? (
          <div className="mt-3">
            <ConfirmCard
              title={t('application.delete.title')}
              hint={t('application.delete.hint', { n: app.events.length })}
              confirmVariant="danger"
              confirmLabel={t('common.delete')}
              busy={del.isPending}
              onCancel={() => {
                del.reset();
                setConfirmingDelete(false);
              }}
              onConfirm={() =>
                del.mutate(undefined, {
                  onSuccess: () => {
                    toast.show(t('toast.application_deleted'));
                    navigate('/pipeline');
                  },
                })
              }
            />
            {del.isError ? <div className="mt-2"><Alert tone="error">{apiMessage(t, del.error)}</Alert></div> : null}
          </div>
        ) : (
          <div className="mt-3">
            <Button variant="ghost" size="sm" className="text-neg-500" onClick={() => setConfirmingDelete(true)}>{t('common.delete')}</Button>
          </div>
        )}
      </PaperCard>
    </div>
  );
}
