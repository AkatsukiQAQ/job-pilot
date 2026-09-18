import type { ReactNode } from 'react';
import { PaperCard } from './PaperCard';

export function EmptyState({ title, hint, action }: { title: string; hint?: string; action?: ReactNode }) {
  return (
    <PaperCard>
      <div className="flex flex-col items-center gap-3 py-10 text-center">
        <h2 className="text-lg font-semibold text-ink-900">{title}</h2>
        {hint ? <p className="max-w-md text-sm text-ink-500">{hint}</p> : null}
        {action}
      </div>
    </PaperCard>
  );
}
