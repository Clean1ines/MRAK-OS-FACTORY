import React from 'react';
import { useNavigate } from 'react-router-dom';

interface HamburgerMenuProps {
  onOpenSidebar: () => void;
}

/**
 * Компонент гамбургер-меню, отображаемый когда боковая панель скрыта.
 * Содержит кнопку открытия панели и ссылку на главную страницу проектов.
 */
export const HamburgerMenu: React.FC<HamburgerMenuProps> = ({ onOpenSidebar }) => {
  const navigate = useNavigate();

  return (
    <div className="fixed top-4 left-4 z-50 flex items-center gap-2">
      <button
        onClick={onOpenSidebar}
        className="p-2 bg-[var(--ios-glass-dark)] backdrop-blur-md border border-[var(--ios-border)] rounded-lg text-[var(--text-muted)] hover:text-[var(--text-main)] transition-colors"
        aria-label="Open sidebar"
      >
        <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <line x1="3" y1="12" x2="21" y2="12" />
          <line x1="3" y1="6" x2="21" y2="6" />
          <line x1="3" y1="18" x2="21" y2="18" />
        </svg>
      </button>
      <button
        onClick={() => navigate('/')}
        className="p-2 bg-[var(--ios-glass-dark)] backdrop-blur-md border border-[var(--ios-border)] rounded-lg text-[var(--text-muted)] hover:text-[var(--text-main)] transition-colors"
        aria-label="Go to projects"
        title="Projects"
      >
        <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M3 9L12 3L21 9V20H15V14H9V20H3V9Z" />
        </svg>
      </button>
    </div>
  );
};
