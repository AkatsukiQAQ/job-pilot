import { Link } from 'react-router-dom';
import { Alert } from '@/components/ui/Alert';
import { EmptyState } from '@/components/ui/EmptyState';
import { PaperCard } from '@/components/ui/PaperCard';
import { useDashboard, useMeta } from '@/hooks/useBoard';
import { useCampaign } from '@/lib/campaign';
import { fmtDate, fmtDateTime } from '@/lib/format';
import { useT } from '@/lib/i18n';
import { STATUS_GROUPS, type StatusGroup } from '@/lib/status';
import type { Dashboard, Kind } from '@/lib/types';

const GREETING_KEY: Partial<Record<Kind, 'dashboard.greeting.intern' | 'dashboard.greeting.newgrad' | 'dashboard.greeting.midcareer'>> = {
  intern: 'dashboard.greeting.intern',
  newgrad: 'dashboard.greeting.newgrad',
  midcareer: 'dashboard.greeting.midcareer',
};

const INTERVIEW_EVENTS = new Set(['interview', 'final_interview', 'casual_interview']);
const GROUP_COLOR: Record<StatusGroup, string> = {
  not_started: 'var(--color-status-considering-bg)',
  in_progress: 'var(--color-status-interviewing-bg)',
  success: 'var(--color-status-accepted-bg)',
  closed: 'var(--color-status-rejected-bg)',
};

function groupCount(d: Dashboard, group: StatusGroup): number {
  return STATUS_GROUPS[group].reduce((n, s) => n + (d.counts_by_status[s] ?? 0), 0);
}

function KpiCard({ label, value, hint, highlight }: { label: string; value: number; hint?: string; highlight?: boolean }) {
  return (
    <div className={['card-paper p-4', highlight ? 'bg-cream-200 ring-2 ring-cream-400' : ''].join(' ')}>
      <div className="text-[11px] font-semibold uppercase tracking-[0.12em] text-ink-500">{label}</div>
      <div className="num mt-1 text-3xl leading-tight text-ink-900 md:text-4xl">{value}</div>
      {hint ? <div className="mt-2 text-xs text-ink-500">{hint}</div> : null}
    </div>
  );
}

function SectionTitle({ children }: { children: string }) {
  return <h2 className="mb-3 text-sm font-semibold text-ink-900">{children}</h2>;
}

export function DashboardPage() {
  const { t, lang } = useT();
  const { current, loaded } = useCampaign();
  const meta = useMeta();
  const dash = useDashboard(current?.campaign_id ?? null);
  const tz = meta.data?.tz ?? 'UTC';
  const now = Date.now();

  if (loaded && !current) {
    return (
      <EmptyState
        title={t('dashboard.empty.title')}
        hint={t('settings.campaigns.empty')}
        action={<Link className="text-sm underline" to="/settings">{t('nav.settings')}</Link>}
      />
    );
  }
  if (dash.isError) return <Alert tone="error">{t('common.error', { message: dash.error.message })}</Alert>;
  if (!dash.data) return <p className="text-sm text-ink-500">{t('common.loading')}</p>;

  const d = dash.data;
  const total = Object.values(d.counts_by_status).reduce((a, b) => a + (b ?? 0), 0);
  const interviews = d.recent_events.filter((e) => {
    const ts = new Date(e.occurred_at).getTime();
    return INTERVIEW_EVENTS.has(e.event_type) && ts >= now && ts <= now + 7 * 86_400_000;
  }).length;
  const deadlines = d.upcoming.filter((u) => u.kind === 'deadline').length;

  return (
    <div className="space-y-5">
      <div>
        <div className="text-[11px] font-semibold uppercase tracking-[0.12em] text-ink-500">
          {t('dashboard.eyebrow')} · {fmtDate(new Date().toISOString(), tz, lang)} · {current?.name}
        </div>
        <h1 className="hand-body mt-1 text-2xl text-ink-900">
          {t((current ? GREETING_KEY[current.kind] : undefined) ?? 'dashboard.greeting')}
        </h1>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard label={t('dashboard.kpi.in_progress')} value={groupCount(d, 'in_progress')} hint={t('dashboard.kpi.hint')} />
        <KpiCard label={t('dashboard.kpi.deadlines')} value={deadlines} />
        <KpiCard label={t('dashboard.kpi.interviews')} value={interviews} />
        <KpiCard label={t('dashboard.kpi.review')} value={0} highlight />
      </div>

      {total === 0 ? (
        <EmptyState
          title={t('dashboard.empty.title')}
          hint={t('dashboard.empty.hint')}
          action={<Link className="text-sm underline" to="/pipeline">{t('nav.pipeline')}</Link>}
        />
      ) : (
        <div className="grid gap-4 lg:grid-cols-12">
          <div className="space-y-4 lg:col-span-8">
            <PaperCard>
              <SectionTitle>{t('dashboard.upcoming')}</SectionTitle>
              {d.upcoming.length === 0 ? (
                <p className="text-sm text-ink-500">{t('dashboard.upcoming.empty')}</p>
              ) : (
                <ul className="divide-y divide-cream-200 text-sm">
                  {d.upcoming.map((u) => (
                    <li key={`${u.application_id}-${u.kind}`} className="flex items-center gap-3 py-2">
                      <span className="w-20 text-xs text-ink-500">{t(`dashboard.upcoming.${u.kind}`)}</span>
                      <Link className="min-w-0 flex-1 truncate text-ink-900 hover:underline" to={`/pipeline/${u.application_id}`}>
                        {u.company}
                        {u.role ? <span className="text-ink-500"> · {u.role}</span> : null}
                        {u.label ? <span className="text-ink-500"> · {u.label}</span> : null}
                      </Link>
                      <span className="font-mono text-xs text-ink-700">{fmtDateTime(u.due, tz, lang)}</span>
                    </li>
                  ))}
                </ul>
              )}
            </PaperCard>

            <PaperCard>
              <SectionTitle>{t('dashboard.recent')}</SectionTitle>
              {d.recent_events.length === 0 ? (
                <p className="text-sm text-ink-500">{t('dashboard.recent.empty')}</p>
              ) : (
                <ul className="divide-y divide-cream-200 text-sm">
                  {d.recent_events.map((e) => (
                    <li key={e.event_id} className="flex items-center gap-3 py-2">
                      <span className="font-mono text-xs text-ink-500">{fmtDateTime(e.occurred_at, tz, lang)}</span>
                      <Link className="min-w-0 flex-1 truncate text-ink-900 hover:underline" to={`/pipeline/${e.application_id}`}>
                        {e.company}
                        <span className="text-ink-500"> · {t(`event.${e.event_type}` as never)}</span>
                        {e.summary ? <span className="text-ink-500"> · {e.summary}</span> : null}
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </PaperCard>
          </div>

          <div className="space-y-4 lg:col-span-4">
            <PaperCard>
              <SectionTitle>{t('dashboard.distribution')}</SectionTitle>
              <div className="flex h-3 overflow-hidden rounded-full bg-cream-200">
                {(Object.keys(STATUS_GROUPS) as StatusGroup[]).map((g) => {
                  const n = groupCount(d, g);
                  return n ? (
                    <div key={g} style={{ width: `${(n / total) * 100}%`, background: GROUP_COLOR[g] }} title={`${t(`group.${g}`)} ${n}`} />
                  ) : null;
                })}
              </div>
              <ul className="mt-3 space-y-1 text-xs text-ink-700">
                {(Object.keys(STATUS_GROUPS) as StatusGroup[]).map((g) => (
                  <li key={g} className="flex items-center gap-2">
                    <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: GROUP_COLOR[g] }} />
                    <span className="flex-1">{t(`group.${g}`)}</span>
                    <span className="font-mono">{groupCount(d, g)}</span>
                  </li>
                ))}
              </ul>
            </PaperCard>
            <PaperCard>
              <SectionTitle>{t('dashboard.soon.hints')}</SectionTitle>
              <div className="pending rounded-[10px] px-3.5 py-4 text-center text-xs leading-[1.7]">
                <span className="font-semibold">{t('dashboard.soon.body')}</span>
              </div>
            </PaperCard>
            <PaperCard>
              <SectionTitle>{t('dashboard.soon.sources')}</SectionTitle>
              <div className="pending rounded-[10px] px-3.5 py-4 text-center text-xs leading-[1.7]">
                <span className="font-semibold">{t('dashboard.soon.body')}</span>
              </div>
            </PaperCard>
          </div>
        </div>
      )}
    </div>
  );
}
