// Navigation tree from docs/design/v1/ia-and-flows.md section 2. Unbuilt pages carry "Soon".
import {
  Brain,
  Briefcase,
  CalendarDays,
  ChevronLeft,
  ChevronRight,
  FlaskConical,
  Inbox,
  MessageCircle,
  NotebookPen,
  PlugZap,
  Settings,
  SquareKanban,
  type LucideIcon,
} from 'lucide-react';
import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import type { Key } from '@/i18n';
import { useT } from '@/lib/i18n';

interface Item {
  to: string;
  label: Key;
  icon: LucideIcon;
  soon?: boolean;
}

const GROUPS: { label: Key; items: Item[] }[] = [
  {
    label: 'nav.group.work',
    items: [
      { to: '/', label: 'nav.dashboard', icon: NotebookPen },
      { to: '/chat', label: 'nav.chat', icon: MessageCircle, soon: true },
      { to: '/pipeline', label: 'nav.pipeline', icon: SquareKanban },
      { to: '/jobs', label: 'nav.jobs', icon: Briefcase, soon: true },
      { to: '/interviews', label: 'nav.interviews', icon: CalendarDays, soon: true },
    ],
  },
  {
    label: 'nav.group.inbox',
    items: [
      { to: '/memory', label: 'nav.memory', icon: Brain, soon: true },
      { to: '/review', label: 'nav.review', icon: Inbox, soon: true },
      { to: '/research', label: 'nav.research', icon: FlaskConical, soon: true },
    ],
  },
  {
    label: 'nav.group.system',
    items: [
      { to: '/settings?tab=sources', label: 'nav.sources', icon: PlugZap },
      { to: '/settings', label: 'nav.settings', icon: Settings },
    ],
  },
];

const KEY = 'jobpilot.nav.collapsed';

/** '/settings' and '/settings?tab=sources' share a route; NavLink can't tell them apart by pathname alone. */
function isActive(item: Item, pathname: string, tab: string | null): boolean {
  if (item.to === '/settings?tab=sources') return pathname === '/settings' && tab === 'sources';
  if (item.to === '/settings') return pathname === '/settings' && tab !== 'sources';
  return pathname === item.to || (item.to !== '/' && pathname.startsWith(item.to + '/'));
}

export function SideNav() {
  const { t } = useT();
  const location = useLocation();
  const tab = new URLSearchParams(location.search).get('tab');
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem(KEY) === '1');
  const toggle = () => {
    localStorage.setItem(KEY, collapsed ? '0' : '1');
    setCollapsed(!collapsed);
  };
  const itemBase =
    'flex flex-shrink-0 items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors md:gap-3';

  return (
    <nav
      className={[
        'flex flex-row items-center gap-1 border-b border-cream-200 p-2 md:h-full md:flex-col md:items-stretch md:border-b-0 md:border-r md:p-4',
        collapsed ? 'md:w-16 md:p-2' : 'md:w-60',
      ].join(' ')}
    >
      <div className="hidden items-center gap-3 px-1 md:mb-6 md:flex">
        <div className="flex h-12 w-12 flex-shrink-0 items-center justify-center">
          <svg
            width="40"
            height="40"
            viewBox="0 0 40 40"
            fill="none"
            stroke="var(--color-ink-900)"
            strokeWidth="1.6"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <path d="M20 3.5C29 3 36.5 10 36.5 19.5S29.5 36.5 20 36.5 3.5 29.5 3.5 20 11 4 20 3.5" />
            <path d="M12 27 14.5 13l5.5 9 5.5-9L28 27" stroke="var(--color-accent-amber)" strokeWidth="2.2" />
          </svg>
        </div>
        {collapsed ? null : (
          <div className="mt-1 min-w-0">
            <div className="hand text-xl leading-[1.05] text-ink-900">Mita JobPilot</div>
            <div className="-mt-0.5 text-[10px] font-semibold uppercase leading-tight tracking-[0.12em] text-ink-500">
              {t('brand.tagline')}
            </div>
          </div>
        )}
      </div>

      <div className="flex w-full flex-row gap-1 overflow-x-auto md:flex-col">
        {GROUPS.map((group) => (
          <div key={group.label} className="flex flex-row gap-1 md:flex-col">
            {collapsed ? null : (
              <div className="hidden px-3 pb-1 pt-3 text-[10px] font-semibold uppercase tracking-[0.12em] text-ink-500 md:block">
                {t(group.label)}
              </div>
            )}
            {group.items.map((item) => {
              const Icon = item.icon;
              const label = t(item.label);
              return item.soon ? (
                <button
                  key={item.to}
                  type="button"
                  aria-disabled="true"
                  aria-label={`${label} · ${t('nav.soon')}`}
                  title={`${label} · ${t('nav.soon')}`}
                  className={`${itemBase} cursor-default text-ink-400`}
                >
                  <Icon size={18} />
                  {collapsed ? (
                    <span className="sr-only">{label}</span>
                  ) : (
                    <>
                      <span>{label}</span>
                      <span className="ml-auto hidden rounded-full bg-cream-200 px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider text-ink-500 md:inline">
                        {t('nav.soon')}
                      </span>
                    </>
                  )}
                </button>
              ) : (
                (() => {
                  const active = isActive(item, location.pathname, tab);
                  return (
                    <Link
                      key={item.to}
                      to={item.to}
                      title={label}
                      aria-current={active ? 'page' : undefined}
                      className={[
                        itemBase,
                        active ? 'bg-cream-300 text-ink-900' : 'text-ink-700 hover:bg-cream-200/60',
                      ].join(' ')}
                    >
                      <Icon size={18} />
                      {collapsed ? <span className="sr-only">{label}</span> : <span>{label}</span>}
                    </Link>
                  );
                })()
              );
            })}
          </div>
        ))}
      </div>

      <button
        type="button"
        onClick={toggle}
        aria-label={collapsed ? t('nav.expand') : t('nav.collapse')}
        className="mt-auto hidden items-center gap-2 rounded-lg border border-cream-200 px-3 py-2 text-xs text-ink-500 hover:bg-cream-100 md:flex"
      >
        {collapsed ? <ChevronRight size={12} /> : <ChevronLeft size={12} />}
        {collapsed ? null : <span>{t('nav.collapse')}</span>}
      </button>
    </nav>
  );
}
