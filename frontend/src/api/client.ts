// frontend/src/api/client.ts
import createClient from 'openapi-fetch';
import type { paths, components } from './generated/schema';

export const client = createClient<paths>({
  baseUrl: '',
  headers: {
    'Content-Type': 'application/json',
  },
  // #CHANGED: Removed setAuthToken - cookies handled automatically by browser
  credentials: 'include', // //ADDED: Include cookies in requests
});

// #CHANGED: Removed setAuthToken function - security risk (localStorage XSS)
// Authentication now handled via httpOnly cookies set by backend

export const api = {
  projects: {
    list: () => client.GET('/api/projects'),
    create: (body: components['schemas']['ProjectCreate']) =>
      client.POST('/api/projects', { body }),
    delete: (projectId: string) =>
      client.DELETE('/api/projects/{project_id}', { params: { path: { project_id: projectId } } }),
  },
  models: {
    list: () => client.GET('/api/models'),
  },
  modes: {
    list: () => client.GET('/api/modes'),
  },
  artifactTypes: {
    list: () => client.GET('/api/artifact-types'),
  },
  artifacts: {
    list: (projectId: string) =>
      client.GET('/api/projects/{project_id}/artifacts', { params: { path: { project_id: projectId } } }),
  },
  messages: {
    list: (projectId: string) =>
      client.GET('/api/projects/{project_id}/messages', { params: { path: { project_id: projectId } } }),
  },
  // //ADDED: Auth endpoints (using raw fetch - not in OpenAPI schema yet)
  auth: {
    login: async (body: { master_key: string }) => {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        credentials: 'include',
      });
      return res.json();
    },
    logout: async () => {
      const res = await fetch('/api/auth/logout', {
        method: 'POST',
        credentials: 'include',
      });
      return res.json();
    },
    session: async () => {
      const res = await fetch('/api/auth/session', {
        credentials: 'include',
      });
      return res.json();
    },
  },
};