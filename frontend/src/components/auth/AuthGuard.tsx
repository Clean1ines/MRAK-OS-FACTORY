// frontend/src/components/auth/AuthGuard.tsx
import React, { useState, useEffect } from 'react';
import { api } from '../../api/client';
import { LoginPage } from './LoginPage';

interface AuthGuardProps {
  children: React.ReactNode;
}

export const AuthGuard: React.FC<AuthGuardProps> = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null);
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    try {
      console.log('🔍 AuthGuard: Checking session, cookies:', document.cookie);
      const res = await api.auth.session();
      console.log('🔍 AuthGuard: Session response:', res);
      setIsAuthenticated(res.authenticated === true);
    } catch (error) {
      console.error('🔍 AuthGuard: Session check failed:', error);
      setIsAuthenticated(false);
    } finally {
      setChecking(false);
    }
  };

  if (checking) {
    return (
      <div className="min-h-screen w-screen flex items-center justify-center bg-[#000000]">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-[#b8956a] border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-[#86868b] text-sm">Checking session...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    console.log('🚫 AuthGuard: Not authenticated, showing LoginPage');
    return <LoginPage />;
  }

  console.log('✅ AuthGuard: Authenticated, rendering children');
  return <>{children}</>;
};