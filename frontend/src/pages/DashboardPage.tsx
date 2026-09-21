import { AlertTriangle, CalendarClock, ListTodo } from 'lucide-react';
import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { DistributionBar } from '@/components/DistributionBar';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { Pill } from '@/components/ui/Chips';
import { EmptyState } from '@/components/ui/EmptyState';
import { PaperCard } from '@/components/ui/PaperCard';
import { useClearNextAction, useDashboard, useMeta } from '@/hooks/useBoard';
import { apiMessage } from '@/lib/api';
import { useCampaign } from '@/lib/campaign';
import { fmtDate, fmtDateTime, relativeDay, timeOfDay } from '@/lib/format';
import { useT } from '@/lib/i18n';
import { STATUS_GROUPS, type StatusGroup } from '@/lib/status';
import { useToast } from '@/lib/toast';
import type { Dashboard, Kind, UpcomingItem } from '@/lib/types';

const GREETING_KEY: Partial<Record<Kind, 'dashboard.greeting.intern' | 'dashboard.greeting.newgrad' | 'dashboard.greeting.midcareer'>> = {
  intern: 'dashboard.greeting.intern',
  newgrad: 'dashboard.greeting.newgrad',
  midcareer: 'dashboard.greeting.midcareer',
};

type UpcomingGroup = 'overdue' | UpcomingItem['kind'];

const UPCOMING_ICON: Record<UpcomingGroup, typeof CalendarClock> = {
  overdue: AlertTriangle,
  deadline: CalendarClock,
  next_action: ListTodo,
};
const GROUP_COLOR: Record<StatusGroup, string> = {
  not_started: 'var(--color-status-considering-bg)',
  in_progress: 'var(--color-status-interviewing-bg)',
  success: 'var(--color-status-accepted-bg)',
  closed: 'var(--color-status-rejected-bg)',
};
const NEG = 'var(--color-neg-500)';
const ROW_LINK = '-mx-2 flex items-center justify-between gap-3 rounded-lg px-2 py-2 hover:bg-cream-100';

function groupCount(d: Dashboard, group: StatusGroup): number {
  return STATUS_GROUPS[group].reduce((n, s) => n + (d.counts_by_status[s] ?? 0), 0);
}

function KpiCard({ label, value, hint, color, highlight }: { label: string; value: ReactNode; hint?: string; color?: string; highlight?: boolean }) {
  return (
    <div className={['card-paper p-4', highlight ? 'bg-cream-200 ring-2 ring-cream-400' : ''].join(' ')}>
      <div className="text-[11px] font-semibold uppercase tracking-[0.12em] text-ink-500">{label}</div>
      <div className="num mt-1 text-3xl leading-tight text-ink-900 md:text-4xl" style={color ? { color } : undefined}>{value}</div>
      {hint ? <div className="mt-2 text-xs text-ink-500">{hint}</div> : null}
    </div>
  );
}

function SectionTitle({ children }: { children: string }) {
  return <h2 className="mb-3 text-sm font-semibold text-ink-900">{children}</h2>;
}

function UpcomingLink({ u, tz, nowIso, className }: { u: UpcomingItem; tz: string; nowIso: string; className?: string }) {
  const { t, lang } = useT();
  const rel = u.overdue ? null : relativeDay(u.due, tz, nowIso);
  return (
    <Link className={[ROW_LINK, className ?? ''].join(' ')} to={`/pipeline/${u.application_id}`}>
      <div className="min-w-0 flex-1">
        <div className="truncate">
          <span className="font-medium text-ink-900">{u.company}</span>
          {u.role ? <span className="text-ink-500"> · {u.role}</span> : null}
        </div>
        {u.label ? <div className="truncate text-xs text-ink-500">{u.label}</div> : null}
      </div>
      <div className="flex flex-shrink-0 flex-col items-end gap-1">
        <span className="font-mono text-xs text-ink-700" style={u.overdue ? { color: NEG } : undefined}>{fmtDateTime(u.due, tz, lang)}</span>
        {rel ? <Pill>{t(`time.${rel}`)}</Pill> : null}
      </div>
    </Link>
  );
}

function NextActionRow({ u, tz, nowIso }: { u: UpcomingItem; tz: string; nowIso: string }) {
  const { t } = useT();
  const toast = useToast();
  const clear = useClearNextAction(u.application_id);
  return (
    <li>
      <div className="flex items-center gap-4">
        <UpcomingLink u={u} tz={tz} nowIso={nowIso} className="flex-1" />
        <Button
          size="sm"
          variant="ghost"
          disabled={clear.isPending}
          onClick={() => clear.mutate(undefined, { onSuccess: () => toast.show(t('toast.next_action_cleared')) })}
        >
          {t('dashboard.upcoming.done')}
        </Button>
      </div>
      {clear.isError ? <div className="mt-1"><Alert tone="error">{apiMessage(t, clear.error)}</Alert></div> : null}
    </li>
  );
}

export function DashboardPage() {
  const { t, lang } = useT();
  const { current, loaded } = useCampaign();
  const meta = useMeta();
  const dash = useDashboard(current?.campaign_id ?? null);
  const tz = current?.tz ?? meta.data?.tz ?? 'UTC';

  if (loaded && !current) {
    return (
      <EmptyState
        title={t('dashboard.empty.title')}
        hint={t('settings.campaigns.empty')}
        action={<Link className="text-sm underline" to="/settings">{t('nav.settings')}</Link>}
      />
    );
  }
  if (dash.isError) {
    return (
      <Alert tone="error">
        <div className="flex items-center justify-between gap-3">
          <span>{apiMessage(t, dash.error)}</span>
          <Button variant="outline" size="sm" onClick={() => dash.refetch()}>{t('common.retry')}</Button>
        </div>
      </Alert>
    );
  }
  if (!dash.data) return <p className="text-sm text-ink-500">{t('common.loading')}</p>;

  const d = dash.data;
  const total = Object.values(d.counts_by_status).reduce((a, b) => a + (b ?? 0), 0);
  const nowIso = new Date().toISOString();
  const tod = timeOfDay(nowIso, tz);
  const upcomingGroups = (['overdue', 'deadline', 'next_action'] as const)
    .map((key) => ({
      key,
      items: d.upcoming.filter((u) => (key === 'overdue' ? u.overdue : !u.overdue && u.kind === key)),
    }))
    .filter((g) => g.items.length > 0);

  return (
    <div className="space-y-5">
      <div>
        <div className="text-[11px] font-semibold uppercase tracking-[0.12em] text-ink-500">
          {t('dashboard.eyebrow')} · {fmtDate(nowIso, tz, lang)} · {current?.name}
        </div>
        <h1 className="hand-body mt-1 text-[40px] leading-tight text-ink-900">
          {t((current ? GREETING_KEY[current.kind] : undefined) ?? 'dashboard.greeting', { tod: t(`time.of_day.${tod}`) })}
          <span className="ml-1 align-[0.6em] text-[0.5em]" style={{ color: 'var(--color-accent-amber)' }}>✦</span>
        </h1>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard label={t('dashboard.kpi.in_progress')} value={groupCount(d, 'in_progress')} hint={t('dashboard.kpi.hint')} />
        <KpiCard
          label={t('dashboard.kpi.deadlines')}
          value={d.deadlines_this_week}
          hint={t('dashboard.kpi.deadlines_hint')}
          color="var(--color-accent-amber)"
        />
        <KpiCard label={t('dashboard.kpi.interviews')} value={d.interviews_next_7d} color="var(--color-accent-olive)" />
        <KpiCard
          label={t('dashboard.kpi.review')}
          value={<span className="pending inline-block px-2 py-0.5 text-sm">—</span>}
          hint={t('common.coming_soon')}
        />
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
                <div className="space-y-4">
                  {upcomingGroups.map((g) => {
                    const Icon = UPCOMING_ICON[g.key];
                    return (
                      <div key={g.key}>
                        <div
                          className="flex items-center gap-2 border-b border-cream-200 pb-1 text-[11px] font-semibold uppercase tracking-[0.12em] text-ink-500"
                          style={g.key === 'overdue' ? { color: NEG } : undefined}
                        >
                          <Icon size={14} />
                          <span>{t(`dashboard.upcoming.${g.key}`)}</span>
                        </div>
                        <ul className="divide-y divide-cream-200 text-sm">
                          {g.items.map((u) =>
                            u.kind === 'next_action' ? (
                              <NextActionRow key={`${u.application_id}-${u.kind}`} u={u} tz={tz} nowIso={nowIso} />
                            ) : (
                              <li key={`${u.application_id}-${u.kind}`}>
                                <UpcomingLink u={u} tz={tz} nowIso={nowIso} />
                              </li>
                            ),
                          )}
                        </ul>
                      </div>
                    );
                  })}
                </div>
              )}
            </PaperCard>

            <PaperCard>
              <SectionTitle>{t('dashboard.recent')}</SectionTitle>
              {d.recent_events.length === 0 ? (
                <p className="text-sm text-ink-500">{t('dashboard.recent.empty')}</p>
              ) : (
                <ul className="divide-y divide-cream-200 text-sm">
                  {d.recent_events.map((e) => (
                    <li key={e.event_id}>
                      <Link className={ROW_LINK} to={`/pipeline/${e.application_id}`}>
                        <span className="min-w-0 flex-1 truncate text-ink-900">
                          {e.company}
                          <span className="text-ink-500"> · {t(`event.${e.event_type}`)}</span>
                          {e.summary ? <span className="text-ink-500"> · {e.summary}</span> : null}
                        </span>
                        <span className="flex-shrink-0 font-mono text-xs text-ink-500">{fmtDateTime(e.occurred_at, tz, lang)}</span>
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
              <DistributionBar
                ariaLabel={t('dashboard.distribution')}
                total={total}
                segments={(Object.keys(STATUS_GROUPS) as StatusGroup[])
                  .map((g) => ({ key: g, count: groupCount(d, g), color: GROUP_COLOR[g] }))
                  .filter((s) => s.count > 0)}
              />
              <ul className="mt-3 space-y-1 text-xs text-ink-700">
                {(Object.keys(STATUS_GROUPS) as StatusGroup[]).map((g) => (
                  <li key={g}>
                    <Link to={`/pipeline?group=${g}`} className="-mx-1 flex items-center gap-2 rounded px-1 hover:bg-cream-100">
                      <span
                        className="inline-block h-2.5 w-2.5 rounded-sm border border-ink-900"
                        style={{ background: GROUP_COLOR[g], transform: 'rotate(-5deg)' }}
                      />
                      <span className="flex-1">{t(`group.${g}`)}</span>
                      <span className="font-mono">{groupCount(d, g)}</span>
                    </Link>
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
