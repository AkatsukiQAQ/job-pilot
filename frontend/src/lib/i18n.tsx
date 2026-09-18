// Flat dictionaries + context, after the MITA Finance prototype's i18n.jsx.
// Language: localStorage > navigator.language (zh / ja) > en.
import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react';
import { DICT, type Key, type Lang } from '@/i18n';

const KEY = 'jobpilot.lang';

function detect(): Lang {
  const stored = localStorage.getItem(KEY);
  if (stored === 'zh' || stored === 'ja' || stored === 'en') return stored;
  const nav = navigator.language.toLowerCase();
  if (nav.startsWith('zh')) return 'zh';
  if (nav.startsWith('ja')) return 'ja';
  return 'en';
}

type T = (key: Key, vars?: Record<string, string | number>) => string;

const Ctx = createContext<{ lang: Lang; setLang: (l: Lang) => void; t: T }>({
  lang: 'en',
  setLang: () => {},
  t: (k) => k,
});

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(detect);
  const setLang = useCallback((l: Lang) => {
    localStorage.setItem(KEY, l);
    document.documentElement.lang = l;
    setLangState(l);
  }, []);
  const value = useMemo(() => {
    document.documentElement.lang = lang;
    const t: T = (key, vars) => {
      const raw = DICT[lang][key] ?? DICT.en[key] ?? key;
      return vars ? raw.replace(/\{(\w+)\}/g, (_, k) => String(vars[k] ?? '')) : raw;
    };
    return { lang, setLang, t };
  }, [lang, setLang]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components -- provider and hook belong together
export function useT() {
  return useContext(Ctx);
}
