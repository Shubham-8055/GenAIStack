import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { PlaygroundProvider } from './context/PlaygroundContext';
import { ThemeProvider } from './context/ThemeContext';
import Dashboard from './pages/Dashboard';
import ProjectSettings from './pages/ProjectSettings';
import DocumentUpload from './pages/DocumentUpload';
import TransactionsList from './pages/TransactionsList';
import Playground from './pages/Playground';
import QueryLogs from './pages/QueryLogs';

function App() {
  return (
    <ThemeProvider>
      <BrowserRouter>
        <PlaygroundProvider>
          <div className="h-screen w-full bg-gray-50 dark:bg-slate-950 transition-colors duration-300">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/project/:projectId/settings" element={<ProjectSettings />} />
              <Route path="/project/:projectId/documents" element={<DocumentUpload />} />
              <Route path="/project/:projectId/transactions" element={<TransactionsList />} />
              <Route path="/project/:projectId/playground" element={<Playground />} />
              <Route path="/project/:projectId/logs" element={<QueryLogs />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </div>
        </PlaygroundProvider>
      </BrowserRouter>
    </ThemeProvider>
  );
}

export default App;
