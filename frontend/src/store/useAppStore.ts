import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface Artifact {
  id: string;
  type: string;
  parent_id: string | null;
  content: any;
  created_at: string;
  updated_at: string;
  version: string;
  status: string;
  summary?: string;
}

export interface Project {
  id: string;
  name: string;
  description: string;
}

export interface Model {
  id: string;
}

export interface Mode {
  id: string;
  name: string;
  default?: boolean;
}

export interface ArtifactType {
  type: string;
  allowed_parents: string[];
  requires_clarification: boolean;
  // другие поля
}

export interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: number;
}

interface AppState {
  projects: Project[];
  currentProjectId: string | null;
  artifacts: Artifact[];
  parentData: Record<string, string>; // id -> type
  currentArtifact: { content: any } | null;
  currentParentId: string | null;
  models: Model[];
  currentClarificationSessionId: string | null;
  artifactTypes: ArtifactType[];
  messages: Message[];
  qTokens: string;
  qReq: string;
  isSimpleMode: boolean;
  selectedModel: string | null;
  selectedArtifactType: string;

  setProjects: (projects: Project[]) => void;
  setCurrentProjectId: (id: string | null) => void;
  setArtifacts: (artifacts: Artifact[]) => void;
  setCurrentArtifact: (artifact: { content: any } | null) => void;
  setCurrentParentId: (id: string | null) => void;
  setModels: (models: Model[]) => void;
  setCurrentClarificationSessionId: (id: string | null) => void;
  setArtifactTypes: (types: ArtifactType[]) => void;
  addMessage: (msg: Message) => void;
  setMessages: (msgs: Message[]) => void;
  setTokens: (tokens: string, req: string) => void;
  setSimpleMode: (isSimple: boolean) => void;
  setSelectedModel: (model: string | null) => void;
  setSelectedArtifactType: (type: string) => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      projects: [],
      currentProjectId: null,
      artifacts: [],
      parentData: {},
      currentArtifact: null,
      currentParentId: null,
      models: [],
      currentClarificationSessionId: null,
      artifactTypes: [],
      messages: [],
      qTokens: '---',
      qReq: '---',
      isSimpleMode: false,
      selectedModel: null,
      selectedArtifactType: 'BusinessIdea',

      setProjects: (projects) => {
        set({ projects });
        // parentData не обновляем, так как она зависит от артефактов
      },
      setCurrentProjectId: (id) => {
        set({ currentProjectId: id, currentClarificationSessionId: null });
        if (id) localStorage.setItem('selectedProjectId', id);
        else localStorage.removeItem('selectedProjectId');
      },
      setArtifacts: (artifacts) => {
        const parentData: Record<string, string> = {};
        artifacts.forEach(a => { parentData[a.id] = a.type; });
        set({ artifacts, parentData });
      },
      setCurrentArtifact: (artifact) => set({ currentArtifact: artifact }),
      setCurrentParentId: (id) => set({ currentParentId: id }),
      setModels: (models) => set({ models }),
      setCurrentClarificationSessionId: (id) => set({ currentClarificationSessionId: id }),
      setArtifactTypes: (types) => set({ artifactTypes: types }),
      addMessage: (msg) => set((state) => ({ messages: [...state.messages, msg] })),
      setMessages: (msgs) => set({ messages: msgs }),
      setTokens: (tokens, req) => set({ qTokens: tokens, qReq: req }),
      setSimpleMode: (isSimple) => set({ isSimpleMode: isSimple }),
      setSelectedModel: (model) => set({ selectedModel: model }),
      setSelectedArtifactType: (type) => set({ selectedArtifactType: type }),
    }),
    {
      name: 'mrak-ui-state',
      partialize: (state) => ({
        currentProjectId: state.currentProjectId,
        selectedModel: state.selectedModel,
        selectedArtifactType: state.selectedArtifactType,
        isSimpleMode: state.isSimpleMode,
      }),
    }
  )
);
