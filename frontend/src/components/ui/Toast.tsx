// Presentational stack for ToastProvider: fixed bottom-right, stacked cards.
import type { ToastItem } from '@/lib/toast';

export function ToastStack({ toasts }: { toasts: ToastItem[] }) {
  if (toasts.length === 0) return null;
  return (
    <div className="pointer-events-none fixed bottom-4 right-4 z-30 flex flex-col gap-2">
      {toasts.map((toast) => (
        <div key={toast.id} role="status" className="card-paper px-3 py-2 text-sm text-ink-900">
          {toast.message}
        </div>
      ))}
    </div>
  );
}
