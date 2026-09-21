// Ephemeral bottom-right notifications for background writes (e.g. "Changes saved").
import { createContext, useCallback, useContext, useRef, useState, type ReactNode } from 'react';
import { ToastStack } from '@/components/ui/Toast';

const MAX_TOASTS = 3;
const DURATION_MS = 3000;
const DURATION_WITH_LINK_MS = 8000;

export interface ToastOptions {
  to?: string;
  toLabel?: string;
}

export interface ToastItem extends ToastOptions {
  id: number;
  message: string;
}

interface Value {
  show: (message: string, opts?: ToastOptions) => void;
}

const Ctx = createContext<Value>({ show: () => {} });

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const nextId = useRef(0);

  const show = useCallback((message: string, opts?: ToastOptions) => {
    const id = nextId.current++;
    setToasts((prev) => [...prev, { id, message, ...opts }].slice(-MAX_TOASTS));
    setTimeout(() => {
      setToasts((prev) => prev.filter((toast) => toast.id !== id));
    }, opts?.to ? DURATION_WITH_LINK_MS : DURATION_MS);
  }, []);

  return (
    <Ctx.Provider value={{ show }}>
      {children}
      <ToastStack toasts={toasts} />
    </Ctx.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components -- provider and hook belong together
export function useToast() {
  return useContext(Ctx);
}
