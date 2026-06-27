import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import MainLayout from './layouts/MainLayout';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import SpecimenPage from './pages/SpecimenPage';
import ResultPage from './pages/ResultPage';
import ResultEntryPage from './pages/ResultEntryPage';
import ReportPage from './pages/ReportPage';
import InstrumentPage from './pages/InstrumentPage';
import BaseDataPage from './pages/BaseDataPage';
import QCPage from './pages/QCPage';
import AuditLogPage from './pages/AuditLogPage';
import UserManagePage from './pages/UserManagePage';
import SettingsPage from './pages/SettingsPage';
import { Spin } from 'antd';

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { token, loading } = useAuth();
  if (loading) return <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}><Spin size="large" /></div>;
  if (!token) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/*"
            element={
              <ProtectedRoute>
                <MainLayout>
                  <Routes>
                    <Route path="/" element={<Navigate to="/dashboard" replace />} />
                    <Route path="/dashboard" element={<DashboardPage />} />
                    <Route path="/specimens" element={<SpecimenPage />} />
                    <Route path="/result-entry" element={<ResultEntryPage />} />
                    <Route path="/results" element={<ResultPage />} />
                    <Route path="/reports" element={<ReportPage />} />
                    <Route path="/instruments" element={<InstrumentPage />} />
                    <Route path="/qc" element={<QCPage />} />
                    <Route path="/audit-logs" element={<AuditLogPage />} />
                    <Route path="/users" element={<UserManagePage />} />
                    <Route path="/settings" element={<SettingsPage />} />
                    <Route path="/base-data" element={<BaseDataPage />} />
                  </Routes>
                </MainLayout>
              </ProtectedRoute>
            }
          />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
