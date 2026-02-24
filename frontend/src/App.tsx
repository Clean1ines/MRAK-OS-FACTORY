// frontend/src/App.tsx
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ChatInterface } from './components/ChatInterface';
import { WorkspacePage } from './components/ios/WorkspacePage';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<ChatInterface />} />
        <Route path="/workspace" element={<WorkspacePage />} />
        <Route path="/workspace.html" element={<Navigate to="/workspace" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;