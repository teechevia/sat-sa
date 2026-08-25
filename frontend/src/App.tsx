import React from 'react';
import { Route, Switch } from 'wouter';
import { AppShell } from './components/AppShell';
import { OverviewPage } from './pages/OverviewPage';
import { OrganizationsPage } from './pages/OrganizationsPage';
import { OrganizationDetailPage } from './pages/OrganizationDetailPage';
import { FindingsPage } from './pages/FindingsPage';
import { FindingDetailPage } from './pages/FindingDetailPage';

export const App: React.FC = () => {
  return (
    <AppShell>
      <Switch>
        <Route path="/" component={OverviewPage} />
        <Route path="/organizations" component={OrganizationsPage} />
        <Route path="/organizations/:id" component={OrganizationDetailPage} />
        <Route path="/findings" component={FindingsPage} />
        <Route path="/findings/:findingId" component={FindingDetailPage} />
        {/* Fallback route */}
        <Route path="/:rest*">
          <OverviewPage />
        </Route>
      </Switch>
    </AppShell>
  );
};

export default App;
