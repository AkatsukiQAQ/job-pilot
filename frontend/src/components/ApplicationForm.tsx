// Shared add/edit form for an application; extracted so Pipeline (add) and Application (edit) pages match.
import { useState, type FormEvent, type ReactNode } from 'react';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { SourceBadge } from '@/components/ui/Chips';
import { Field, inputClass } from '@/components/ui/Field';
import { isoToZonedInput, zonedInputToIso } from '@/lib/format';
import { useT } from '@/lib/i18n';
import type { ApplicationDetail, ApplicationPatch, Status, Track } from '@/lib/types';

export interface ApplicationFormValues extends ApplicationPatch {
  initial_status: Status | null;
}

interface Props {
  mode: 'add' | 'edit';
  initial?: ApplicationDetail;
  tz: string;
  tracks: Track[];
  statuses: Status[];
  /** Initial track for mode 'add'; falls back to `tracks[0]`. */
  defaultTrack?: Track;
  busy?: boolean;
  error?: ReactNode;
  onSubmit: (values: ApplicationFormValues) => void;
  onCancel: () => void;
}

interface FormState {
  company_name: string;
  role: string;
  track: Track;
  job_url: string;
  notes: string;
  initial_status: string;
  deadline_at: string;
  next_action: string;
  next_action_due: string;
  portal_url: string;
}

function initialState(
  mode: 'add' | 'edit',
  initial: ApplicationDetail | undefined,
  tz: string,
  tracks: Track[],
  defaultTrack: Track | undefined,
): FormState {
  if (mode === 'edit' && initial) {
    return {
      company_name: initial.company,
      role: initial.role ?? '',
      track: initial.track,
      job_url: initial.job_url ?? '',
      notes: initial.notes ?? '',
      initial_status: '',
      deadline_at: initial.deadline_at ? isoToZonedInput(initial.deadline_at, tz) : '',
      next_action: initial.next_action ?? '',
      next_action_due: initial.next_action_due ? isoToZonedInput(initial.next_action_due, tz) : '',
      portal_url: initial.portal_url ?? '',
    };
  }
  return {
    company_name: '',
    role: '',
    track: defaultTrack ?? tracks[0] ?? 'other',
    job_url: '',
    notes: '',
    initial_status: '',
    deadline_at: '',
    next_action: '',
    next_action_due: '',
    portal_url: '',
  };
}

export function ApplicationForm({ mode, initial, tz, tracks, statuses, defaultTrack, busy, error, onSubmit, onCancel }: Props) {
  const { t } = useT();
  const [form, setForm] = useState<FormState>(() => initialState(mode, initial, tz, tracks, defaultTrack));
  const [companyError, setCompanyError] = useState(false);
  const set = (k: keyof FormState) => (e: { target: { value: string } }) => {
    setForm((prev) => ({ ...prev, [k]: e.target.value }));
    if (k === 'company_name' && companyError) setCompanyError(false);
  };

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (!form.company_name.trim()) {
      setCompanyError(true);
      return;
    }
    onSubmit({
      company_name: form.company_name.trim(),
      role: form.role.trim() || null,
      track: form.track,
      job_url: form.job_url.trim() || null,
      notes: form.notes.trim() || null,
      portal_url: form.portal_url.trim() || null,
      deadline_at: form.deadline_at ? zonedInputToIso(form.deadline_at, tz) : null,
      next_action: form.next_action.trim() || null,
      next_action_due: form.next_action_due ? zonedInputToIso(form.next_action_due, tz) : null,
      initial_status: form.initial_status ? (form.initial_status as Status) : null,
    });
  };

  return (
    <form onSubmit={submit} className="grid gap-4 md:grid-cols-2">
      {mode === 'edit' ? (
        <h2 className="text-sm font-semibold text-ink-900 md:col-span-2">{t('application.edit.title')}</h2>
      ) : null}
      <Field label={t('pipeline.form.company')}>
        <input className={inputClass} autoFocus value={form.company_name} onChange={set('company_name')} />
      </Field>
      <Field label={`${t('pipeline.form.role')} (${t('common.optional')})`}>
        <input className={inputClass} value={form.role} onChange={set('role')} />
      </Field>
      <Field label={t('pipeline.form.track')}>
        <select className={inputClass} value={form.track} onChange={set('track')}>
          {tracks.map((tr) => (
            <option key={tr} value={tr}>{t(`track.${tr}`)}</option>
          ))}
        </select>
      </Field>
      <Field label={`${t('pipeline.form.job_url')} (${t('common.optional')})`}>
        <input className={inputClass} type="url" value={form.job_url} onChange={set('job_url')} />
      </Field>
      {mode === 'add' ? (
        <Field label={t('application.form.initial_status')}>
          <select className={inputClass} value={form.initial_status} onChange={set('initial_status')}>
            <option value="">{t('status.unrecorded')}</option>
            {statuses.filter((s) => s !== 'unrecorded').map((s) => (
              <option key={s} value={s}>{t(`status.${s}`)}</option>
            ))}
          </select>
        </Field>
      ) : null}
      {mode === 'edit' ? (
        <>
          <Field label={`${t('application.form.deadline')} (${t('common.optional')})`} hint={t('time.tz_hint', { tz })}>
            <input className={inputClass} type="datetime-local" value={form.deadline_at} onChange={set('deadline_at')} />
          </Field>
          <Field label={`${t('application.form.next_action')} (${t('common.optional')})`}>
            <input className={inputClass} maxLength={120} value={form.next_action} onChange={set('next_action')} />
          </Field>
          <Field label={`${t('application.form.next_action_due')} (${t('common.optional')})`}>
            <input className={inputClass} type="datetime-local" value={form.next_action_due} onChange={set('next_action_due')} />
          </Field>
          <Field label={`${t('application.form.portal_url')} (${t('common.optional')})`}>
            <input className={inputClass} type="url" value={form.portal_url} onChange={set('portal_url')} />
          </Field>
        </>
      ) : null}
      <div className="md:col-span-2">
        <Field label={`${t('pipeline.form.notes')} (${t('common.optional')})`}>
          <textarea className={inputClass} rows={2} value={form.notes} onChange={set('notes')} />
        </Field>
      </div>
      <div className="flex items-center gap-2 text-xs text-ink-500 md:col-span-2">
        <SourceBadge source="manual" /> {t('common.source_note')}
      </div>
      {companyError ? (
        <div className="md:col-span-2"><Alert tone="error">{t('pipeline.form.required')}</Alert></div>
      ) : null}
      {error ? <div className="md:col-span-2">{error}</div> : null}
      <div className="flex justify-end gap-2 md:col-span-2">
        <Button variant="ghost" onClick={onCancel}>{t('common.cancel')}</Button>
        <Button type="submit" disabled={busy}>{t(mode === 'add' ? 'common.add' : 'common.save')}</Button>
      </div>
    </form>
  );
}
