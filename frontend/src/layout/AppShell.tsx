import { Outlet } from 'react-router-dom';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { apiMessage } from '@/lib/api';
import { CampaignProvider, useCampaign } from '@/lib/campaign';
import { useT } from '@/lib/i18n';
import { ToastProvider } from '@/lib/toast';
import { SideNav } from './SideNav';
import { TopBar } from './TopBar';

function MainContent() {
  const { t } = useT();
  const { error, refetch } = useCampaign();
  return (
    <main className="flex-1 overflow-y-auto p-4 md:p-6 md:pr-gutter">
      {error ? (
        <Alert tone="error">
          <div className="flex items-center justify-between gap-3">
            <span>{apiMessage(t, error)}</span>
            <Button variant="outline" size="sm" onClick={() => refetch()}>
              {t('common.retry')}
            </Button>
          </div>
        </Alert>
      ) : null}
      <Outlet />
    </main>
  );
}

export function AppShell() {
  return (
    <CampaignProvider>
      <ToastProvider>
        <div className="flex h-full flex-col md:flex-row">
          <SideNav />
          <div className="flex min-w-0 flex-1 flex-col">
            <TopBar />
            <MainContent />
          </div>
        </div>
      </ToastProvider>
    </CampaignProvider>
  );
}
