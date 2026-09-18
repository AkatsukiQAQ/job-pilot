// Small labelled marks: status chip (12 states), source badge, generic pill, "pending" placeholder.
import { Calendar, FileArchive, FileInput, Mail, MessageCircle, PencilLine } from 'lucide-react';
import type { ReactNode } from 'react';
import { useT } from '@/lib/i18n';
import { sourceIconColor, statusStyle } from '@/lib/status';
import type { Source, Status } from '@/lib/types';

export function Pill({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <span
      className={[
        'inline-flex items-center gap-1.5 rounded-full bg-cream-200 px-2 py-0.5 text-[11px] font-semibold text-ink-700',
        className ?? '',
      ].join(' ')}
    >
      {children}
    </span>
  );
}

export function StatusChip({
  status,
  autoStatus,
}: {
  status: Status;
  /** When given and different from `status`, shows the "set by you" pencil with a tooltip. */
  autoStatus?: Status;
}) {
  const { t } = useT();
  const overridden = autoStatus !== undefined && autoStatus !== status;
  return (
    <span className="inline-flex items-center gap-1.5">
      <span
        className="chip inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold"
        style={statusStyle(status)}
      >
        {t(`status.${status}`)}
      </span>
      {overridden ? (
        <span
          title={`${t('common.overridden')} · ${t('common.overridden.hint', { status: t(`status.${autoStatus}`) })}`}
          className="inline-flex h-5 w-5 items-center justify-center rounded-full"
          style={{ background: 'var(--color-override-bg)', color: 'var(--color-override-fg)' }}
        >
          <PencilLine size={12} />
        </span>
      ) : null}
    </span>
  );
}

const SOURCE_ICON: Record<Source, typeof Mail> = {
  gmail: Mail,
  gcal: Calendar,
  linkedin_export: FileArchive,
  manual: PencilLine,
  chat: MessageCircle,
  import: FileInput,
  system: FileInput,
};

export function SourceBadge({ source }: { source: Source }) {
  const { t } = useT();
  const Icon = SOURCE_ICON[source] ?? PencilLine;
  return (
    <span
      className="badge inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px]"
      style={{ background: 'var(--color-source-bg)', color: 'var(--color-source-fg)' }}
    >
      <Icon size={11} style={{ color: sourceIconColor(source) }} />
      {t(`source.${source}`)}
    </span>
  );
}

/** "待确认" placeholder for missing information; never a status. */
export function Pending() {
  const { t } = useT();
  return <span className="pending inline-block px-2 py-0.5 text-xs">{t('common.pending')}</span>;
}
