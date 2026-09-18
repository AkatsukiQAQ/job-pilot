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
import { NavLink } from 'react-router-dom';
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
      { to: '/sources', label: 'nav.sources', icon: PlugZap, soon: true },
      { to: '/settings', label: 'nav.settings', icon: Settings },
    ],
  },
];

const KEY = 'jobpilot.nav.collapsed';

export function SideNav() {
  const { t } = useT();
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
        <div
          className="hand flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-full text-2xl text-cream-50"
          style={{ background: 'var(--color-accent-amber)' }}
        >
          M
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
                <span
                  key={item.to}
                  title={`${label} · ${t('nav.soon')}`}
                  className={`${itemBase} cursor-default text-ink-400`}
                >
                  <Icon size={18} />
                  {collapsed ? null : (
                    <>
                      <span>{label}</span>
                      <span className="ml-auto hidden rounded-full bg-cream-200 px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider text-ink-500 md:inline">
                        {t('nav.soon')}
                      </span>
                    </>
                  )}
                </span>
              ) : (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.to === '/'}
                  title={label}
                  className={({ isActive }) =>
                    [
                      itemBase,
                      isActive ? 'bg-cream-300 text-ink-900' : 'text-ink-700 hover:bg-cream-200/60',
                    ].join(' ')
                  }
                >
                  <Icon size={18} />
                  {collapsed ? null : <span>{label}</span>}
                </NavLink>
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
