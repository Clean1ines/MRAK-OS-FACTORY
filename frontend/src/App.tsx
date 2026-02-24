// frontend/src/App.tsx
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ChatInterface } from './components/ChatInterface';
import { WorkspacePage } from './components/ios/WorkspacePage';
import { AuthGuard } from './components/auth/AuthGuard';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public route - login page */}
        <Route path="/login" element={
          <LoginPage />
        } />
        
        {/* Protected routes */}
        <Route path="/" element={
          <AuthGuard>
            <ChatInterface />
          </AuthGuard>
        } />
        
        <Route path="/workspace" element={
          <AuthGuard>
            <WorkspacePage />
          </AuthGuard>
        } />
        
        <Route path="/workspace.html" element={<Navigate to="/workspace" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;