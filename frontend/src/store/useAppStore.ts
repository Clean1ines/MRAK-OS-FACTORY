import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface Artifact {
  id: string;
  type: string;
  parent_id: string | null;
  // #CHANGED: any -> Record<string, unknown> | null (более конкретно)
  content: Record<string, unknown> | null;
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
  parentData: Record<string, string>;
  currentArtifact: { content: unknown } | null;
  currentParentId: string | null;
  models: Model[];
  modes: Mode[];
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
  setCurrentArtifact: (artifact: { content: unknown } | null) => void;
  setCurrentParentId: (id: string | null) => void;
  setModels: (models: Model[]) => void;
  setModes: (modes: Mode[]) => void;
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
    (set) => ({
      projects: [],
      currentProjectId: null,
      artifacts: [],
      parentData: {},
      currentArtifact: null,
      currentParentId: null,
      models: [],
      modes: [],
      currentClarificationSessionId: null,
      artifactTypes: [],
      messages: [],
      qTokens: '---',
      qReq: '---',
      isSimpleMode: false,
      selectedModel: null,
      selectedArtifactType: 'BusinessIdea',

      setProjects: (projects) => set({ projects }),
      setCurrentProjectId: (id) => {
        set({ currentProjectId: id, currentClarificationSessionId: null });
        if (id) localStorage.setItem('selectedProjectId', id);
        else localStorage.removeItem('selectedProjectId');
      },
      setArtifacts: (artifacts) => {
        const parentData: Record<string, string> = {};
        artifacts.forEach((a) => {
          parentData[a.id] = a.type;
        });
        set({ artifacts, parentData });
      },
      setCurrentArtifact: (artifact) => set({ currentArtifact: artifact }),
      setCurrentParentId: (id) => set({ currentParentId: id }),
      setModels: (models) => set({ models }),
      setModes: (modes) => set({ modes }),
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
