import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface Artifact {
  id: string;
  type: string;
  parent_id: string | null;
  content: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
  version: string;
  status: string;
  summary?: string;
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

export interface ChatMessageData {
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
}

interface AppState {
  artifacts: Artifact[];
  parentData: Record<string, string>;
  currentArtifact: { content: unknown } | null;
  currentParentId: string | null;
  models: Model[];
  modes: Mode[];
  currentClarificationSessionId: string | null;
  artifactTypes: ArtifactType[];
  qTokens: string;
  qReq: string;
  isSimpleMode: boolean;
  selectedModel: string | null;
  selectedArtifactType: string;
  // Chat State
  messages: ChatMessageData[];

  setArtifacts: (artifacts: Artifact[]) => void;
  setCurrentArtifact: (artifact: { content: unknown } | null) => void;
  setCurrentParentId: (id: string | null) => void;
  setModels: (models: Model[]) => void;
  setModes: (modes: Mode[]) => void;
  setCurrentClarificationSessionId: (id: string | null) => void;
  setArtifactTypes: (types: ArtifactType[]) => void;
  setTokens: (tokens: string, req: string) => void;
  setSimpleMode: (isSimple: boolean) => void;
  setSelectedModel: (model: string | null) => void;
  setSelectedArtifactType: (type: string) => void;
  // Chat Actions
  setMessages: (messages: ChatMessageData[]) => void;
  addMessage: (message: ChatMessageData) => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      artifacts: [],
      parentData: {},
      currentArtifact: null,
      currentParentId: null,
      models: [],
      modes: [],
      currentClarificationSessionId: null,
      artifactTypes: [],
      qTokens: '---',
      qReq: '---',
      isSimpleMode: false,
      selectedModel: null,
      selectedArtifactType: 'BusinessIdea',
      messages: [],

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
      setTokens: (tokens, req) => set({ qTokens: tokens, qReq: req }),
      setSimpleMode: (isSimple) => set({ isSimpleMode: isSimple }),
      setSelectedModel: (model) => set({ selectedModel: model }),
      setSelectedArtifactType: (type) => set({ selectedArtifactType: type }),
      setMessages: (messages) => set({ messages }),
      addMessage: (msg) => set((state) => ({ messages: [...state.messages, msg] })),
    }),
    {
      name: 'mrak-ui-state',
      partialize: (state) => ({
        selectedModel: state.selectedModel,
        selectedArtifactType: state.selectedArtifactType,
        isSimpleMode: state.isSimpleMode,
      }),
    }
  )
);
