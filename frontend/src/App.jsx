import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import SafeNavigation from './pages/SafeNavigation';
import ImageLogs from './pages/ImageLogs';
import Analytics from './pages/Analytics';
import Maintenance from './pages/Maintenance';
import Alerts from './pages/Alerts';
import AdminReports from './pages/AdminReports';
import CitizenReport from './pages/CitizenReport';
import Settings from './pages/Settings';
import Admin from './pages/Admin';
import { LiveDataProvider } from './context/LiveDataContext';

function App() {
  return (
    <LiveDataProvider>
      <Router>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="navigation" element={<SafeNavigation />} />
            <Route path="image-logs" element={<ImageLogs />} />
            <Route path="analytics" element={<Analytics />} />
            <Route path="maintenance" element={<Maintenance />} />
            <Route path="alerts" element={<Alerts />} />
            <Route path="user-reports" element={<AdminReports />} />
            <Route path="report" element={<CitizenReport />} />
            <Route path="settings" element={<Settings />} />
            <Route path="admin" element={<Admin />} />
          </Route>
        </Routes>
      </Router>
    </LiveDataProvider>
  );
}

export default App;
