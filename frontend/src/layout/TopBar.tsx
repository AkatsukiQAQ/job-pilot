import { Moon, Sun } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { LANGS, LANG_LABEL, type Lang } from '@/i18n';
import { useCampaign } from '@/lib/campaign';
import { useT } from '@/lib/i18n';
import { useTheme } from '@/lib/theme';

const selectClass =
  'rounded-lg border border-cream-200 bg-cream-50 px-2 py-1.5 text-sm text-ink-900 focus:outline-none focus:ring-2 focus:ring-ink-900/15';

export function TopBar() {
  const { t, lang, setLang } = useT();
  const { campaigns, current, select } = useCampaign();
  const [theme, setTheme] = useTheme();
  const navigate = useNavigate();

  return (
    <header className="flex h-14 items-center gap-3 border-b border-cream-200 px-4 md:px-6 md:pr-gutter">
      <label className="flex items-center gap-2 text-xs text-ink-500">
        <span className="hidden font-semibold uppercase tracking-wide sm:inline">{t('top.campaign')}</span>
        <select
          className={selectClass}
          value={current?.campaign_id ?? ''}
          onChange={(e) => {
            if (e.target.value === 'manage') navigate('/settings');
            else select(Number(e.target.value));
          }}
        >
          {campaigns.length === 0 ? <option value="">{t('top.campaign.none')}</option> : null}
          {campaigns.map((c) => (
            <option key={c.campaign_id} value={c.campaign_id}>
              {c.name} · {t(`kind.${c.kind}`)} · {c.application_count}
            </option>
          ))}
          <option value="manage">{t('top.campaign.manage')}</option>
        </select>
      </label>

      <div className="ml-auto flex items-center gap-2">
        <select
          className={selectClass}
          value={lang}
          onChange={(e) => setLang(e.target.value as Lang)}
          aria-label="language"
        >
          {LANGS.map((l) => (
            <option key={l} value={l}>
              {LANG_LABEL[l]}
            </option>
          ))}
        </select>
        <button
          type="button"
          onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
          aria-label={theme === 'dark' ? t('top.theme.light') : t('top.theme.dark')}
          className="rounded-lg p-2 text-ink-700 hover:bg-cream-100"
        >
          {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
        </button>
      </div>
    </header>
  );
}
