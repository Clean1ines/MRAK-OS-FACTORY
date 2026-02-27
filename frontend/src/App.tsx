import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ChatInterface } from './components/ChatInterface';
import { WorkspacePage } from './components/ios/WorkspacePage';
import { AuthGuard } from './components/auth/AuthGuard';
import { LoginPage } from './components/auth/LoginPage';
import { ProtectedLayout } from './components/layout/ProtectedLayout';
import { Toast } from './components/common/Toast';

class ErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { hasError: boolean }
> {
  constructor(props: { children: React.ReactNode }) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('Uncaught error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen w-screen flex items-center justify-center bg-[#000000] text-white">
          <div className="text-center p-8">
            <h2 className="text-2xl font-bold text-[#b8956a] mb-4">Что-то пошло не так</h2>
            <p className="text-[#86868b] mb-6">
              Произошла непредвиденная ошибка. Пожалуйста, обновите страницу.
            </p>
            <button
              onClick={() => window.location.reload()}
              className="px-4 py-2 bg-[#b8956a] text-black rounded hover:bg-[#d4b48a] transition-colors"
            >
              Обновить страницу
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />

          {/* Главная страница с сайдбаром проектов и чатом */}
          <Route
            path="/"
            element={
              <AuthGuard>
                <ProtectedLayout />
              </AuthGuard>
            }
          >
            <Route index element={<ChatInterface />} />
          </Route>

          {/* Workspace — отдельная страница без общего сайдбара */}
          <Route
            path="/workspace"
            element={
              <AuthGuard>
                <WorkspacePage />
              </AuthGuard>
            }
          />

          <Route path="/workspace.html" element={<Navigate to="/workspace" replace />} />
        </Routes>
      </BrowserRouter>
      <Toast />
    </ErrorBoundary>
  );
}

export default App;
