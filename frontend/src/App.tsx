import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ChatInterface } from './components/ChatInterface';
import { WorkspacePage } from './components/ios/WorkspacePage';
import { AuthGuard } from './components/auth/AuthGuard';
import { LoginPage } from './components/auth/LoginPage';
import { Toast } from './components/common/Toast'; // CHANGED: named import

// Простой ErrorBoundary для отлова ошибок рендера
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
    // Логируем ошибку, но не показываем пользователю технические детали
    console.error('Uncaught error:', error, errorInfo);
    // Можно также отправить в Sentry или аналоги
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
          {/* Public route - login page */}
          <Route path="/login" element={<LoginPage />} />

          {/* Protected routes */}
          <Route
            path="/"
            element={
              <AuthGuard>
                <ChatInterface />
              </AuthGuard>
            }
          />

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
      <Toast /> {/* Глобальные тосты */}
    </ErrorBoundary>
  );
}

export default App;
