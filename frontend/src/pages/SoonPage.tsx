import { EmptyState } from '@/components/ui/EmptyState';
import { useT } from '@/lib/i18n';

export function SoonPage() {
  const { t } = useT();
  return <EmptyState title={t('soon.title')} hint={t('soon.hint')} />;
}
