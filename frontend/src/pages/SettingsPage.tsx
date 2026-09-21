import { useState, type FormEvent } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { Pill, SourceBadge } from '@/components/ui/Chips';
import { ConfirmCard } from '@/components/ui/ConfirmCard';
import { EmptyState } from '@/components/ui/EmptyState';
import { Field, inputClass } from '@/components/ui/Field';
import { PageHeader } from '@/components/ui/PageHeader';
import { PaperCard } from '@/components/ui/PaperCard';
import { Segmented } from '@/components/ui/Segmented';
import { useActivateCampaign, useCreateCampaign, useDeleteCampaign, useMeta, useUpdateCampaign } from '@/hooks/useBoard';
import { LANGS, LANG_LABEL, type Lang } from '@/i18n';
import { apiMessage } from '@/lib/api';
import { useCampaign } from '@/lib/campaign';
import { useT } from '@/lib/i18n';
import { useTheme } from '@/lib/theme';
import { useToast } from '@/lib/toast';
import type { Campaign, CampaignIn, Kind } from '@/lib/types';

const DELETE_TOKEN = 'DELETE';

/** Create (no `initial`) or edit (with `initial`) a cycle; same fields either way. */
function CampaignForm({ initial, onDone }: { initial?: Campaign; onDone: () => void }) {
  const { t } = useT();
  const meta = useMeta();
  const create = useCreateCampaign();
  const update = useUpdateCampaign();
  const { select } = useCampaign();
  const toast = useToast();
  const [form, setForm] = useState({
    name: initial?.name ?? '',
    kind: initial?.kind ?? meta.data?.kinds[0] ?? ('' as Kind),
    region_pack: initial?.region_pack ?? meta.data?.region_packs[0] ?? '',
    starts_on: initial?.starts_on ?? '',
    ends_on: initial?.ends_on ?? '',
  });
  const [invalid, setInvalid] = useState(false);
  const set = (k: keyof typeof form) => (e: { target: { value: string } }) => setForm({ ...form, [k]: e.target.value });
  const pending = create.isPending || update.isPending;
  const error = create.error ?? update.error;

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (!meta.data) return;
    const name = form.name.trim();
    setInvalid(!name);
    if (!name) return;
    const body: CampaignIn = {
      name,
      kind: form.kind || meta.data.kinds[0],
      region_pack: form.region_pack || meta.data.region_packs[0],
      starts_on: form.starts_on || null,
      ends_on: form.ends_on || null,
    };
    if (initial) {
      update.mutate(
        { id: initial.campaign_id, body },
        { onSuccess: () => { toast.show(t('toast.campaign_updated')); onDone(); } },
      );
    } else {
      create.mutate(body, {
        onSuccess: (c) => { select(c.campaign_id); toast.show(t('toast.campaign_created')); onDone(); },
      });
    }
  };

  return (
    <form onSubmit={submit} className="grid gap-4 md:grid-cols-2">
      <Field label={t('settings.campaigns.name')}>
        <input
          className={inputClass}
          value={form.name}
          onChange={(e) => {
            set('name')(e);
            setInvalid(false);
          }}
          aria-invalid={invalid || undefined}
        />
      </Field>
      <Field label={t('settings.campaigns.kind')}>
        <select className={inputClass} value={form.kind} onChange={set('kind')}>
          {(meta.data?.kinds ?? []).map((k) => <option key={k} value={k}>{t(`kind.${k}`)}</option>)}
        </select>
      </Field>
      <Field label={t('settings.campaigns.region')}>
        <select className={inputClass} value={form.region_pack} onChange={set('region_pack')}>
          {(meta.data?.region_packs ?? []).map((p) => <option key={p} value={p}>{p}</option>)}
        </select>
      </Field>
      <div className="grid grid-cols-2 gap-3">
        <Field label={t('settings.campaigns.starts')}>
          <input className={inputClass} type="date" value={form.starts_on} onChange={set('starts_on')} />
        </Field>
        <Field label={`${t('settings.campaigns.ends')} (${t('common.optional')})`} hint={t('settings.campaigns.ends.hint')}>
          <input className={inputClass} type="date" value={form.ends_on} onChange={set('ends_on')} />
        </Field>
      </div>
      {invalid ? <div className="md:col-span-2"><Alert tone="error">{t('api.validation_failed')}</Alert></div> : null}
      {error ? <div className="md:col-span-2"><Alert tone="error">{apiMessage(t, error)}</Alert></div> : null}
      <div className="flex justify-end gap-2 md:col-span-2">
        <Button variant="ghost" onClick={onDone}>{t('common.cancel')}</Button>
        <Button type="submit" disabled={pending || !meta.data}>{initial ? t('common.save') : t('common.add')}</Button>
      </div>
    </form>
  );
}

type SettingsTab = 'sources' | 'settings';

export function SettingsPage() {
  const { t, lang, setLang } = useT();
  const [theme, setTheme] = useTheme();
  const meta = useMeta();
  const { campaigns, select } = useCampaign();
  const activate = useActivateCampaign();
  const del = useDeleteCampaign();
  const toast = useToast();
  const [creating, setCreating] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [deleteStep, setDeleteStep] = useState<1 | 2>(1);
  const [typed, setTyped] = useState('');
  const resetDelete = () => {
    setDeletingId(null);
    setDeleteStep(1);
    setTyped('');
    del.reset();
  };
  const [params, setParams] = useSearchParams();
  const tab: SettingsTab = params.get('tab') === 'sources' ? 'sources' : 'settings';
  const setTab = (next: SettingsTab) => setParams(next === 'settings' ? {} : { tab: next });

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow={t('settings.eyebrow')}
        title={tab === 'sources' ? t('nav.sources') : t('settings.title')}
        actions={
          <Segmented
            value={tab}
            onChange={setTab}
            options={[
              { value: 'sources', label: t('settings.tab.sources') },
              { value: 'settings', label: t('settings.tab.settings') },
            ]}
            ariaLabel={t('settings.title')}
          />
        }
      />

      {tab === 'sources' ? (
        <EmptyState
          title={t('settings.sources.title')}
          hint={t('settings.sources.body')}
          action={
            <div className="flex items-center gap-2">
              <div className="flex gap-2 opacity-70">
                <SourceBadge source="gmail" />
                <SourceBadge source="gcal" />
                <SourceBadge source="linkedin_export" />
              </div>
              <span className="pending inline-block px-2 py-0.5 text-[11px] font-medium">{t('common.coming_soon')}</span>
            </div>
          }
        />
      ) : (
        <>
      <PaperCard>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-ink-900">{t('settings.campaigns')}</h2>
          {creating ? null : <Button size="sm" onClick={() => setCreating(true)}>{t('settings.campaigns.new')}</Button>}
        </div>
        {creating ? <div className="mb-4"><CampaignForm onDone={() => setCreating(false)} /></div> : null}
        {activate.isError ? <div className="mb-3"><Alert tone="error">{apiMessage(t, activate.error)}</Alert></div> : null}
        {campaigns.length === 0 ? (
          <p className="text-sm text-ink-500">{t('settings.campaigns.empty')}</p>
        ) : (
          <div className="overflow-hidden rounded-2xl border border-cream-200 bg-cream-100">
            <table className="w-full text-sm">
              <thead className="bg-cream-200/60 text-left text-xs uppercase tracking-wide text-ink-500">
                <tr>
                  <th className="px-4 py-2 font-semibold">{t('settings.campaigns.name')}</th>
                  <th className="px-4 py-2 font-semibold">{t('settings.campaigns.kind')}</th>
                  <th className="px-4 py-2 font-semibold">{t('settings.campaigns.region')}</th>
                  <th className="px-4 py-2 font-semibold">{t('settings.campaigns.starts')} / {t('settings.campaigns.ends')}</th>
                  <th className="px-4 py-2 text-right font-semibold">{t('settings.campaigns.count')}</th>
                  <th className="px-4 py-2" />
                </tr>
              </thead>
              <tbody className="divide-y divide-cream-200">
                {campaigns.map((c) => {
                  if (editingId === c.campaign_id) {
                    return (
                      <tr key={c.campaign_id}>
                        <td colSpan={6} className="px-4 py-4">
                          <CampaignForm initial={c} onDone={() => setEditingId(null)} />
                        </td>
                      </tr>
                    );
                  }
                  if (deletingId === c.campaign_id) {
                    return (
                      <tr key={c.campaign_id}>
                        <td colSpan={6} className="px-4 py-4">
                          <ConfirmCard
                            title={t('settings.campaigns.delete')}
                            hint={t('settings.campaigns.delete.step1', { name: c.name, n: c.application_count })}
                            busy={del.isPending}
                            confirmVariant="danger"
                            confirmLabel={deleteStep === 1 ? t('settings.campaigns.delete.confirm') : t('settings.campaigns.delete.final')}
                            confirmDisabled={deleteStep === 2 && typed !== DELETE_TOKEN}
                            onCancel={resetDelete}
                            onConfirm={() => {
                              if (deleteStep === 1) {
                                setDeleteStep(2);
                                return;
                              }
                              del.mutate(c.campaign_id, {
                                onSuccess: () => {
                                  resetDelete();
                                  toast.show(t('toast.campaign_deleted'));
                                },
                              });
                            }}
                          >
                            {deleteStep === 2 ? (
                              <Field label={t('settings.campaigns.delete.type_delete')}>
                                <input
                                  className={inputClass}
                                  value={typed}
                                  onChange={(e) => setTyped(e.target.value)}
                                  autoFocus
                                />
                              </Field>
                            ) : null}
                            {del.isError ? <div className="mt-3"><Alert tone="error">{apiMessage(t, del.error)}</Alert></div> : null}
                          </ConfirmCard>
                        </td>
                      </tr>
                    );
                  }
                  return (
                    <tr key={c.campaign_id}>
                      <td className="px-4 py-3 text-ink-900">{c.name}{c.is_active ? <Pill className="ml-2">{t('settings.campaigns.active')}</Pill> : null}</td>
                      <td className="px-4 py-3 text-ink-700">{t(`kind.${c.kind}`)}</td>
                      <td className="px-4 py-3 font-mono text-xs text-ink-700">{c.region_pack}</td>
                      <td className="px-4 py-3 font-mono text-xs text-ink-700">
                        {c.starts_on ?? t('common.none')} → {c.ends_on ?? <span className="font-sans">{t('settings.campaigns.ongoing')}</span>}
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-ink-700">{c.application_count}</td>
                      <td className="px-4 py-3 text-right whitespace-nowrap">
                        <Button size="sm" variant="ghost" onClick={() => setEditingId(c.campaign_id)}>{t('settings.campaigns.edit')}</Button>
                        {c.is_active ? null : (
                          <Button
                            size="sm"
                            variant="outline"
                            className="ml-2"
                            disabled={activate.isPending}
                            onClick={() =>
                              activate.mutate(c.campaign_id, {
                                onSuccess: () => {
                                  select(c.campaign_id);
                                  toast.show(t('toast.campaign_activated'));
                                },
                              })
                            }
                          >
                            {t('settings.campaigns.activate')}
                          </Button>
                        )}
                        <Button
                          size="sm"
                          variant="ghost"
                          className="ml-2 text-neg-500"
                          onClick={() => {
                            resetDelete();
                            setDeletingId(c.campaign_id);
                          }}
                        >
                          {t('settings.campaigns.delete')}
                        </Button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </PaperCard>

      <PaperCard>
        <h2 className="mb-3 text-sm font-semibold text-ink-900">{t('settings.prefs')}</h2>
        <div className="grid gap-4 md:grid-cols-3">
          <Field label={t('settings.prefs.language')}>
            <select className={inputClass} value={lang} onChange={(e) => setLang(e.target.value as Lang)}>
              {LANGS.map((l) => <option key={l} value={l}>{LANG_LABEL[l]}</option>)}
            </select>
          </Field>
          <Field label={t('settings.prefs.theme')}>
            <select className={inputClass} value={theme} onChange={(e) => setTheme(e.target.value as 'light' | 'dark')}>
              <option value="light">{t('top.theme.light')}</option>
              <option value="dark">{t('top.theme.dark')}</option>
            </select>
          </Field>
          <Field label={t('settings.prefs.tz')} hint={t('settings.prefs.tz.hint')}>
            <input className={inputClass} readOnly value={meta.data?.tz ?? ''} />
          </Field>
        </div>
      </PaperCard>
        </>
      )}
    </div>
  );
}
