// Inline confirmation: summary, before (struck through) -> after (highlighted), confirm / cancel.
// Takes focus on mount and hands it back on unmount; Escape cancels, Enter inside children confirms.
import { useEffect, useId, useRef, type KeyboardEvent, type ReactNode } from 'react';
import { Button } from './Button';
import { SourceBadge } from './Chips';
import { useT } from '@/lib/i18n';

interface Props {
  title: string;
  before?: ReactNode;
  after?: ReactNode;
  hint?: string;
  busy?: boolean;
  eyebrow?: string;
  badge?: ReactNode;
  confirmVariant?: 'primary' | 'danger';
  confirmLabel?: string;
  confirmDisabled?: boolean;
  children?: ReactNode;
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmCard({
  title,
  before,
  after,
  hint,
  busy,
  eyebrow,
  badge,
  confirmVariant = 'primary',
  confirmLabel,
  confirmDisabled,
  children,
  onConfirm,
  onCancel,
}: Props) {
  const { t } = useT();
  const titleId = useId();
  const ref = useRef<HTMLElement>(null);

  useEffect(() => {
    const previous = document.activeElement;
    ref.current?.focus();
    return () => {
      if (previous instanceof HTMLElement) previous.focus();
    };
  }, []);

  const onKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'Escape') {
      e.stopPropagation();
      onCancel();
    }
  };
  const canConfirm = !busy && !confirmDisabled;

  return (
    <section
      ref={ref}
      role="group"
      aria-labelledby={titleId}
      tabIndex={-1}
      onKeyDown={onKeyDown}
      className="card-paper px-5 py-[18px] focus:outline-none focus-visible:ring-2 focus-visible:ring-ink-900/30"
    >
      <div className="mb-2 flex items-center justify-between">
        <span className="text-[11px] font-semibold uppercase tracking-[0.12em] text-ink-500">
          {eyebrow ?? t('application.confirm.eyebrow')}
        </span>
        {badge ?? <SourceBadge source="manual" />}
      </div>
      <div id={titleId} className="text-sm font-semibold text-ink-900">{title}</div>
      {before !== undefined && after !== undefined ? (
        <div className="mt-3 grid grid-cols-2 gap-3 text-sm">
          <div>
            <div className="text-[11px] font-semibold uppercase tracking-wide text-ink-500">
              {t('application.confirm.before')}
            </div>
            <div className="mt-1 line-through" style={{ color: 'var(--color-diff-before-fg)' }}>
              {before}
            </div>
          </div>
          <div>
            <div className="text-[11px] font-semibold uppercase tracking-wide text-ink-500">
              {t('application.confirm.after')}
            </div>
            <div
              className="mt-1 inline-block rounded px-1.5"
              style={{ background: 'var(--color-diff-after-bg)', color: 'var(--color-diff-after-fg)' }}
            >
              {after}
            </div>
          </div>
        </div>
      ) : null}
      {hint ? <p className="mt-3 text-xs text-ink-500">{hint}</p> : null}
      {children !== undefined && children !== null ? (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (canConfirm) onConfirm();
          }}
        >
          {children}
        </form>
      ) : null}
      <div className="mt-4 flex justify-end gap-2">
        <Button variant="ghost" size="sm" onClick={onCancel} disabled={busy}>
          {t('common.cancel')}
        </Button>
        <Button variant={confirmVariant} size="sm" onClick={onConfirm} disabled={!canConfirm}>
          {confirmLabel ?? t('common.confirm')}
        </Button>
      </div>
    </section>
  );
}
