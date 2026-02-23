import { useEffect } from 'react';
import ThemeEffects from './styles/ThemeEffects';
import { useAppStore } from './store/useAppStore';
import { useProjectData } from './hooks/useProjectData';
import { useNotification } from './hooks/useNotifications';
import { Notification } from './components/Notification';
import { ChatCanvas } from './components/ChatCanvas';
import { client } from './api/client';

function App() {
  const store = useAppStore();
  const { showNotification } = useNotification();
  useProjectData(); // загружает проекты, модели, типы и артефакты

  const handleCreateProject = async () => {
    const name = prompt('Введите название проекта:');
    if (!name) return;
    try {
      const res = await client.POST('/api/projects', {
        body: { name, description: '' },
      });
      if (res.error) throw new Error(res.error.error || 'Ошибка создания');
      // обновим список проектов через refetch или добавим вручную
      // можно просто перезагрузить страницу или добавить через store
      store.setProjects([...store.projects, { id: res.data.id!, name, description: '' }]);
      store.setCurrentProjectId(res.data.id!);
      showNotification('Проект создан', 'success');
    } catch (e: any) {
      showNotification(e.message, 'error');
    }
  };

  const handleDeleteProject = async () => {
    if (!store.currentProjectId) return;
    if (!confirm('Удалить проект? Все артефакты будут безвозвратно удалены.')) return;
    try {
      const res = await client.DELETE('/api/projects/{project_id}', {
        params: { path: { project_id: store.currentProjectId } },
      });
      if (res.error) throw new Error(res.error.error || 'Ошибка удаления');
      store.setProjects(store.projects.filter(p => p.id !== store.currentProjectId));
      store.setCurrentProjectId(null);
      store.setMessages([]);
      showNotification('Проект удалён', 'success');
    } catch (e: any) {
      showNotification(e.message, 'error');
    }
  };

  return (
    <div className="relative h-screen w-screen bg-[#010509] text-mrak-text font-mono overflow-hidden flex flex-col">
      <ThemeEffects />

      {/* NAV */}
      <nav className="h-14 flex items-center justify-between px-6 shrink-0 bg-mrak-nav backdrop-blur-md border-b border-white/5 z-10">
        <div className="flex gap-6">
          <div className="flex flex-col">
            <span className="text-[8px] tracking-widest text-mrak-cyan uppercase">Prompt_Mode</span>
            <span className="text-xs">FACTORY_V2</span>
          </div>
          <div className="flex flex-col">
            <span className="text-[8px] tracking-widest text-mrak-cyan uppercase">Neural_Model</span>
            <select
              className="bg-transparent border border-cyan-800/30 rounded px-2 py-1 text-xs outline-none focus:border-cyan-500"
              value={store.selectedModel || ''}
              onChange={(e) => store.setSelectedModel(e.target.value)}
            >
              <option value="">-- Выберите модель --</option>
              {store.models.map((m) => (
                <option key={m.id} value={m.id}>{m.id}</option>
              ))}
            </select>
          </div>
        </div>
        <div className="text-xs text-mrak-cyan/60">
          TOKENS: <b className="text-mrak-cyan">{store.qTokens}</b> | REQ: <b>{store.qReq}</b>
        </div>
      </nav>

      {/* PROJECT PANEL */}
      <div className="px-6 py-3 border-b border-white/5 flex items-center gap-4 shrink-0 z-10">
        <span className="text-sm text-cyan-400">Проект:</span>
        <select
          className="bg-black/50 border border-cyan-800/30 rounded px-2 py-1 text-xs outline-none focus:border-cyan-500"
          value={store.currentProjectId || ''}
          onChange={(e) => store.setCurrentProjectId(e.target.value || null)}
        >
          <option value="">-- Выберите --</option>
          {store.projects.map((p) => (
            <option key={p.id} value={p.id}>{p.name}</option>
          ))}
        </select>
        <button onClick={handleCreateProject} className="text-xs border border-cyan-600/50 px-2 py-1 rounded hover:bg-cyan-900/50">Новый</button>
        <button onClick={handleDeleteProject} className="text-xs border border-red-600/50 px-2 py-1 rounded hover:bg-red-900/50">Удалить</button>

        <div className="flex-1" />
        <div className="flex border border-cyan-600/30 rounded overflow-hidden">
          <button
            className={`px-3 py-1 text-xs ${store.isSimpleMode ? 'bg-cyan-600/30 text-cyan-300' : 'text-zinc-500'}`}
            onClick={() => store.setSimpleMode(true)}
          >
            Простой
          </button>
          <button
            className={`px-3 py-1 text-xs ${!store.isSimpleMode ? 'bg-cyan-600/30 text-cyan-300' : 'text-zinc-500'}`}
            onClick={() => store.setSimpleMode(false)}
          >
            Расширенный
          </button>
        </div>
      </div>

      {/* MAIN CONTENT */}
      <main className="flex-1 overflow-hidden z-10">
        {store.isSimpleMode ? (
          <div className="h-full p-4">
            <ChatCanvas />
          </div>
        ) : (
          <div className="h-full p-4">
            <div className="border border-cyan-800/30 rounded-lg p-4 h-full overflow-auto">
              <p className="text-cyan-600">Расширенный режим в разработке</p>
            </div>
          </div>
        )}
      </main>

      <Notification />
    </div>
  );
}

export default App;
