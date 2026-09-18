import { useState, type FormEvent } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { Pill, SourceBadge } from '@/components/ui/Chips';
import { EmptyState } from '@/components/ui/EmptyState';
import { Field, inputClass } from '@/components/ui/Field';
import { PageHeader } from '@/components/ui/PageHeader';
import { PaperCard } from '@/components/ui/PaperCard';
import { useActivateCampaign, useCreateCampaign, useMeta, useUpdateCampaign } from '@/hooks/useBoard';
import { LANGS, LANG_LABEL, type Lang } from '@/i18n';
import { useCampaign } from '@/lib/campaign';
import { useT } from '@/lib/i18n';
import { useTheme } from '@/lib/theme';
import type { Campaign, CampaignIn, Kind } from '@/lib/types';

/** Create (no `initial`) or edit (with `initial`) a cycle; same fields either way. */
function CampaignForm({ initial, onDone }: { initial?: Campaign; onDone: () => void }) {
  const { t } = useT();
  const meta = useMeta();
  const create = useCreateCampaign();
  const update = useUpdateCampaign();
  const { select } = useCampaign();
  const [form, setForm] = useState({
    name: initial?.name ?? '',
    kind: initial?.kind ?? ('newgrad' as Kind),
    region_pack: initial?.region_pack ?? 'global_en',
    starts_on: initial?.starts_on ?? '',
    ends_on: initial?.ends_on ?? '',
  });
  const set = (k: keyof typeof form) => (e: { target: { value: string } }) => setForm({ ...form, [k]: e.target.value });
  const pending = create.isPending || update.isPending;
  const error = create.error ?? update.error;

  const submit = (e: FormEvent) => {
    e.preventDefault();
    const body: CampaignIn = { ...form, starts_on: form.starts_on || null, ends_on: form.ends_on || null };
    if (initial) update.mutate({ id: initial.campaign_id, body }, { onSuccess: onDone });
    else create.mutate(body, { onSuccess: (c) => { select(c.campaign_id); onDone(); } });
  };

  return (
    <form onSubmit={submit} className="grid gap-4 md:grid-cols-2">
      <Field label={t('settings.campaigns.name')}>
        <input className={inputClass} required value={form.name} onChange={set('name')} />
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
      {error ? <div className="md:col-span-2"><Alert tone="error">{error.message}</Alert></div> : null}
      <div className="flex justify-end gap-2 md:col-span-2">
        <Button variant="ghost" onClick={onDone}>{t('common.cancel')}</Button>
        <Button type="submit" disabled={pending}>{initial ? t('common.save') : t('common.add')}</Button>
      </div>
    </form>
  );
}

const SOURCE_TABS = ['sources', 'settings'] as const;
type SettingsTab = (typeof SOURCE_TABS)[number];

function SegmentedTabs({ tab, onChange }: { tab: SettingsTab; onChange: (tab: SettingsTab) => void }) {
  const { t } = useT();
  return (
    <div role="tablist" className="inline-flex rounded-full border border-cream-200 bg-cream-100 p-1 text-sm">
      {SOURCE_TABS.map((tb) => (
        <button
          key={tb}
          type="button"
          role="tab"
          aria-selected={tab === tb}
          onClick={() => onChange(tb)}
          className={[
            'rounded-full px-4 py-1.5 font-medium transition-colors',
            tab === tb ? 'bg-cream-300 text-ink-900' : 'text-ink-500 hover:text-ink-700',
          ].join(' ')}
        >
          {t(`settings.tab.${tb}`)}
        </button>
      ))}
    </div>
  );
}

export function SettingsPage() {
  const { t, lang, setLang } = useT();
  const [theme, setTheme] = useTheme();
  const meta = useMeta();
  const { campaigns } = useCampaign();
  const activate = useActivateCampaign();
  const [creating, setCreating] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [params, setParams] = useSearchParams();
  const tab: SettingsTab = params.get('tab') === 'sources' ? 'sources' : 'settings';
  const setTab = (next: SettingsTab) => setParams(next === 'settings' ? {} : { tab: next });

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow={t('settings.eyebrow')}
        title={tab === 'sources' ? t('nav.sources') : t('settings.title')}
        actions={<SegmentedTabs tab={tab} onChange={setTab} />}
      />

      {tab === 'sources' ? (
        <EmptyState
          title={t('settings.sources.title')}
          hint={t('settings.sources.body')}
          action={
            <div className="flex gap-2 opacity-70">
              <SourceBadge source="gmail" />
              <SourceBadge source="gcal" />
              <SourceBadge source="linkedin_export" />
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
                {campaigns.map((c) =>
                  editingId === c.campaign_id ? (
                    <tr key={c.campaign_id}>
                      <td colSpan={6} className="px-4 py-4">
                        <CampaignForm initial={c} onDone={() => setEditingId(null)} />
                      </td>
                    </tr>
                  ) : (
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
                          <Button size="sm" variant="outline" className="ml-2" disabled={activate.isPending} onClick={() => activate.mutate(c.campaign_id)}>
                            {t('settings.campaigns.activate')}
                          </Button>
                        )}
                      </td>
                    </tr>
                  ),
                )}
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
