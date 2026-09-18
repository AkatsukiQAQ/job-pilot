import { createBrowserRouter } from 'react-router-dom';
import { AppShell } from '@/layout/AppShell';
import { ApplicationPage } from '@/pages/ApplicationPage';
import { DashboardPage } from '@/pages/DashboardPage';
import { PipelinePage } from '@/pages/PipelinePage';
import { SettingsPage } from '@/pages/SettingsPage';
import { SoonPage } from '@/pages/SoonPage';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <AppShell />,
    children: [
      { index: true, element: <DashboardPage /> },
      { path: 'pipeline', element: <PipelinePage /> },
      { path: 'pipeline/:id', element: <ApplicationPage /> },
      { path: 'settings', element: <SettingsPage /> },
      // IA routes that arrive in later steps render a placeholder.
      { path: '*', element: <SoonPage /> },
    ],
  },
]);
