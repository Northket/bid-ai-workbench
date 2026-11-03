import { useEffect } from 'react';
import { Route, Routes } from 'react-router-dom';
import AppLayout from './layouts/AppLayout';
import Dashboard from './pages/Dashboard';
import Projects from './pages/Projects';
import ProjectDetail from './pages/ProjectDetail';
import Announcements from './pages/Announcements';
import Documents from './pages/Documents';
import ParseWorkbench from './pages/ParseWorkbench';
import Requirements from './pages/Requirements';
import History from './pages/History';
import AiChat from './pages/AiChat';
import BidList from './pages/BidList';
import BidDetail from './pages/BidDetail';
import Settings from './pages/Settings';
import { setErrorNotifier } from './api/client';
import { App } from 'antd';

export default function AppRoot() {
  const { message } = App.useApp();
  useEffect(() => {
    setErrorNotifier((msg) => message.error(msg));
  }, [message]);

  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/projects" element={<Projects />} />
        <Route path="/projects/:id" element={<ProjectDetail />} />
        <Route path="/announcements" element={<Announcements />} />
        <Route path="/documents" element={<Documents />} />
        <Route path="/documents/:id/parse" element={<ParseWorkbench />} />
        <Route path="/requirements" element={<Requirements />} />
        <Route path="/history" element={<History />} />
        <Route path="/ai" element={<AiChat />} />
        <Route path="/bids" element={<BidList />} />
        <Route path="/bids/:id" element={<BidDetail />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="*" element={<Dashboard />} />
      </Route>
    </Routes>
  );
}
