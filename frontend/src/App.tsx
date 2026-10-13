import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Sidebar } from './components/Sidebar';
import { DashboardPage } from './pages/DashboardPage';
import { NewDiscussionPage } from './pages/NewDiscussionPage';
import { DiscussionDetailPage } from './pages/DiscussionDetailPage';
import { CompareModelsPage } from './pages/CompareModelsPage';
import { DebatePage } from './pages/DebatePage';
import { ResearchWorkspacePage } from './pages/ResearchWorkspacePage';
import { DocumentsPage } from './pages/DocumentsPage';
import { ConversationHistoryPage } from './pages/ConversationHistoryPage';
import { ProviderSettingsPage } from './pages/ProviderSettingsPage';
import { UsageCostPage } from './pages/UsageCostPage';
import { SettingsPage } from './pages/SettingsPage';

export function App() {
  return (
    <BrowserRouter>
      <div className="flex min-h-screen bg-slate-950 text-slate-100 font-sans selection:bg-emerald-500 selection:text-slate-950">
        <Sidebar />
        <main className="flex-1 min-w-0 overflow-y-auto">
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/new-discussion" element={<NewDiscussionPage />} />
            <Route path="/discussions/:id" element={<DiscussionDetailPage />} />
            <Route path="/compare" element={<CompareModelsPage />} />
            <Route path="/debate" element={<DebatePage />} />
            <Route path="/research" element={<ResearchWorkspacePage />} />
            <Route path="/documents" element={<DocumentsPage />} />
            <Route path="/history" element={<ConversationHistoryPage />} />
            <Route path="/providers" element={<ProviderSettingsPage />} />
            <Route path="/usage" element={<UsageCostPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
