import { useCallback } from 'react';
import { create } from 'zustand';

interface Notification {
  id: number;
  message: string;
  type: 'info' | 'error' | 'success';
}

interface NotificationStore {
  notifications: Notification[];
  addNotification: (message: string, type: 'info' | 'error' | 'success') => void;
  removeNotification: (id: number) => void;
}

const useNotificationStore = create<NotificationStore>((set) => ({
  notifications: [],
  addNotification: (message, type) => {
    const id = Date.now();
    set((state) => ({ notifications: [...state.notifications, { id, message, type }] }));
    setTimeout(() => {
      set((state) => ({ notifications: state.notifications.filter(n => n.id !== id) }));
    }, 3000);
  },
  removeNotification: (id) => set((state) => ({ notifications: state.notifications.filter(n => n.id !== id) })),
}));

export const useNotification = () => {
  const addNotification = useNotificationStore((s) => s.addNotification);
  const showNotification = useCallback((message: string, type: 'info' | 'error' | 'success' = 'info') => {
    addNotification(message, type);
  }, [addNotification]);
  return { showNotification };
};

export { useNotificationStore };
