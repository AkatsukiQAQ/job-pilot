import { Moon, Sun } from 'lucide-react';
import { CycleSwitcher } from '@/components/CycleSwitcher';
import { LANGS } from '@/i18n';
import { useT } from '@/lib/i18n';
import { useTheme } from '@/lib/theme';

export function TopBar() {
  const { t, lang, setLang } = useT();
  const [theme, setTheme] = useTheme();

  return (
    <header className="flex h-14 items-center gap-3 border-b border-cream-200 px-4 md:px-6 md:pr-gutter">
      <div className="flex items-center gap-2 text-xs text-ink-500">
        <span className="hidden font-semibold uppercase tracking-wide sm:inline">{t('top.campaign')}</span>
        <CycleSwitcher />
      </div>

      <div className="ml-auto flex items-center gap-2">
        <div role="tablist" aria-label={t('settings.prefs.language')} className="inline-flex rounded-full border border-cream-200 bg-cream-100 p-0.5 text-xs">
          {LANGS.map((l) => (
            <button
              key={l}
              type="button"
              role="tab"
              aria-selected={lang === l}
              onClick={() => setLang(l)}
              className={
                lang === l
                  ? 'rounded-full bg-cream-300 px-2.5 py-1 font-semibold text-ink-900'
                  : 'rounded-full px-2.5 py-1 text-ink-500 hover:text-ink-700'
              }
            >
              {t(`lang.short.${l}` as never)}
            </button>
          ))}
        </div>
        <button
          type="button"
          onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
          aria-label={t('top.theme.toggle')}
          className="rounded-lg p-2 text-ink-700 hover:bg-cream-100"
        >
          {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
        </button>
        <span aria-hidden className="ml-1 inline-block h-8 w-8 rounded-full border border-ink-200" style={{ background: 'var(--color-cream-300)' }} />
      </div>
    </header>
  );
}
