// Dark mode lives on <html data-theme="dark"> (tokens.css requirement), remembered in localStorage.
import { useCallback, useState } from 'react';

export type Theme = 'light' | 'dark';
const KEY = 'jobpilot.theme';

function read(): Theme {
  return localStorage.getItem(KEY) === 'dark' ? 'dark' : 'light';
}

function apply(theme: Theme) {
  if (theme === 'dark') document.documentElement.dataset.theme = 'dark';
  else delete document.documentElement.dataset.theme;
}

export function applyStoredTheme() {
  apply(read());
}

export function useTheme(): [Theme, (t: Theme) => void] {
  const [theme, set] = useState<Theme>(read);
  const setTheme = useCallback((t: Theme) => {
    localStorage.setItem(KEY, t);
    apply(t);
    set(t);
  }, []);
  return [theme, setTheme];
}
