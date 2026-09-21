// Presentational stack for ToastProvider: fixed bottom-right, stacked cards.
// The live region stays mounted even when empty so screen readers announce later toasts.
import { Check } from 'lucide-react';
import { Link } from 'react-router-dom';
import type { ToastItem } from '@/lib/toast';

export function ToastStack({ toasts }: { toasts: ToastItem[] }) {
  return (
    <div aria-live="polite" aria-atomic="false" className="fixed bottom-4 right-4 z-30 flex flex-col gap-2">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className="card-paper flex items-center gap-2 px-3 py-2 text-sm"
          style={{ background: 'var(--color-pos-50)', color: 'var(--color-pos-500)' }}
        >
          <Check size={14} aria-hidden />
          <span>{toast.message}</span>
          {toast.to && toast.toLabel ? (
            <Link to={toast.to} className="font-medium underline">
              {toast.toLabel}
            </Link>
          ) : null}
        </div>
      ))}
    </div>
  );
}
