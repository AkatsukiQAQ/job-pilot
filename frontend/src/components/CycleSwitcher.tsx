import { CalendarDays, Check, ChevronDown } from 'lucide-react';
import { useEffect, useRef, useState, type KeyboardEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { useCampaign } from '@/lib/campaign';
import { useT } from '@/lib/i18n';

/** Cycle switcher (components.md §14): trigger + listbox menu, keyboard-navigable. */
export function CycleSwitcher() {
  const { t } = useT();
  const { campaigns, current, select } = useCampaign();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const wasOpen = useRef(false);

  useEffect(() => {
    if (!open) return;
    const opts = menuRef.current?.querySelectorAll<HTMLButtonElement>('[data-option]');
    if (!opts || opts.length === 0) return;
    const idx = campaigns.findIndex((c) => c.campaign_id === current?.campaign_id);
    (opts[idx >= 0 ? idx : 0] ?? opts[0])?.focus();
  }, [open, campaigns, current]);

  useEffect(() => {
    if (open) {
      wasOpen.current = true;
      return;
    }
    if (wasOpen.current) {
      wasOpen.current = false;
      triggerRef.current?.focus();
    }
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onMouseDown = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) setOpen(false);
    };
    const onKeyDown = (e: globalThis.KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false);
    };
    document.addEventListener('mousedown', onMouseDown);
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('mousedown', onMouseDown);
      document.removeEventListener('keydown', onKeyDown);
    };
  }, [open]);

  const moveFocus = (idx: number, dir: 1 | -1) => {
    const opts = menuRef.current?.querySelectorAll<HTMLButtonElement>('[data-option]');
    if (!opts || opts.length === 0) return;
    opts[(idx + dir + opts.length) % opts.length]?.focus();
  };

  const onOptionKeyDown = (e: KeyboardEvent<HTMLButtonElement>, idx: number) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      moveFocus(idx, 1);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      moveFocus(idx, -1);
    }
  };

  return (
    <div
      ref={containerRef}
      className="relative"
      onBlur={(e) => {
        if (e.relatedTarget instanceof Node && !containerRef.current?.contains(e.relatedTarget)) setOpen(false);
      }}
    >
      <button
        ref={triggerRef}
        type="button"
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        className="inline-flex items-center gap-1.5 rounded-lg border border-cream-200 bg-cream-50 px-3 py-1.5 text-sm text-ink-900 hover:bg-cream-100"
      >
        <CalendarDays size={14} className="text-ink-500" />
        <span>{current?.name ?? t('top.campaign.none')}</span>
        <ChevronDown size={14} />
      </button>
      {open ? (
        <div ref={menuRef} role="listbox" aria-label={t('top.campaign')} className="card-paper absolute right-0 z-20 mt-1 w-80 p-1">
          {campaigns.map((c, idx) => {
            const isCurrent = c.campaign_id === current?.campaign_id;
            return (
              <button
                key={c.campaign_id}
                type="button"
                role="option"
                aria-selected={isCurrent}
                data-option
                onClick={() => {
                  select(c.campaign_id);
                  setOpen(false);
                }}
                onKeyDown={(e) => onOptionKeyDown(e, idx)}
                className="w-full rounded-lg px-3 py-2 text-left hover:bg-cream-100"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className={`text-sm text-ink-900 ${isCurrent ? 'font-medium' : ''}`}>{c.name}</span>
                  {isCurrent ? <Check size={14} className="text-ink-900" /> : null}
                </div>
                <div className="text-[11px] text-ink-500">
                  {t(`kind.${c.kind}`)} · {c.region_pack} ·{' '}
                  <span className="font-mono">
                    {c.starts_on ?? t('common.none')} → {c.ends_on ?? t('settings.campaigns.ongoing')}
                  </span>{' '}
                  · {t('common.applications_count', { n: c.application_count })}
                </div>
              </button>
            );
          })}
          <button
            type="button"
            onClick={() => {
              setOpen(false);
              navigate('/settings');
            }}
            className="w-full border-t border-cream-200 px-3 py-2 text-left text-[13px] text-ink-700 hover:bg-cream-100"
          >
            {t('top.campaign.manage')}
          </button>
        </div>
      ) : null}
    </div>
  );
}
