import React from 'react';
import { Outlet } from 'react-router-dom';
import { ProjectsSidebar } from '../projects/ProjectsSidebar';

/**
 * Общий layout для защищённых страниц.
 * Содержит боковую панель проектов и область для вложенного контента.
 */
export const ProtectedLayout: React.FC = () => {
  return (
    <div className="flex h-screen">
      <ProjectsSidebar />
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
};
