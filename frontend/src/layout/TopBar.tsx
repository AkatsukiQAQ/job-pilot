import { Moon, Sun } from 'lucide-react';
import { CycleSwitcher } from '@/components/CycleSwitcher';
import { Button } from '@/components/ui/Button';
import { Segmented } from '@/components/ui/Segmented';
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
        <Segmented
          size="sm"
          value={lang}
          onChange={setLang}
          options={LANGS.map((l) => ({ value: l, label: t(`lang.short.${l}` as never) }))}
          ariaLabel={t('settings.prefs.language')}
        />
        <Button
          size="icon"
          variant="ghost"
          onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
          aria-label={t('top.theme.toggle')}
        >
          {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
        </Button>
        <span aria-hidden className="ml-1 inline-block h-8 w-8 rounded-full border border-ink-200" style={{ background: 'var(--color-cream-300)' }} />
      </div>
    </header>
  );
}
