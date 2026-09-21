import { createBrowserRouter, useParams } from 'react-router-dom';
import { AppShell } from '@/layout/AppShell';
import { ApplicationPage } from '@/pages/ApplicationPage';
import { DashboardPage } from '@/pages/DashboardPage';
import { PipelinePage } from '@/pages/PipelinePage';
import { SettingsPage } from '@/pages/SettingsPage';
import { SoonPage } from '@/pages/SoonPage';

// Remount per id so page-local state (edit modes, drafts) never leaks between applications.
// eslint-disable-next-line react-refresh/only-export-components -- route wrapper belongs with the route table
function ApplicationRoute() {
  const { id } = useParams();
  return <ApplicationPage key={id} />;
}

export const router = createBrowserRouter([
  {
    path: '/',
    element: <AppShell />,
    children: [
      { index: true, element: <DashboardPage /> },
      { path: 'pipeline', element: <PipelinePage /> },
      { path: 'pipeline/:id', element: <ApplicationRoute /> },
      { path: 'settings', element: <SettingsPage /> },
      // IA routes that arrive in later steps render a placeholder.
      { path: '*', element: <SoonPage /> },
    ],
  },
]);
