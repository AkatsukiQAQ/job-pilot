import type { Status } from '@/lib/types';

// The 12 statuses in board order, grouped as the design's four bands (D14).
export type StatusGroup = 'not_started' | 'in_progress' | 'success' | 'closed';

export const STATUS_GROUPS: Record<StatusGroup, Status[]> = {
  not_started: ['unrecorded', 'considering', 'preparing'],
  in_progress: ['applied', 'assessment', 'interviewing'],
  success: ['offer', 'accepted', 'joined'],
  closed: ['unsuitable', 'withdrawn', 'rejected'],
};

export const STATUS_ORDER: Status[] = Object.values(STATUS_GROUPS).flat();

export function groupOf(status: Status): StatusGroup {
  return (Object.keys(STATUS_GROUPS) as StatusGroup[]).find((g) =>
    STATUS_GROUPS[g].includes(status),
  )!;
}

/** Inline CSS variables from tokens.css; avoids 36 literal Tailwind class strings. */
export function statusStyle(status: Status) {
  return {
    color: `var(--color-status-${status}-fg)`,
    background: `var(--color-status-${status}-bg)`,
    borderColor: `var(--color-status-${status}-border)`,
  };
}

const SOURCE_VAR: Record<string, string> = {
  gmail: 'gmail',
  gcal: 'calendar',
  linkedin_export: 'linkedin',
  manual: 'manual',
  chat: 'chat',
  import: 'import',
  system: 'import',
};

export function sourceIconColor(source: string) {
  return `var(--color-source-${SOURCE_VAR[source] ?? 'manual'})`;
}
