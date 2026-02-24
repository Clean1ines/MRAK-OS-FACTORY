// frontend/src/api/client.ts
import createClient from 'openapi-fetch';
import type { paths, components } from './generated/schema';
import { createTimeoutMiddleware } from './fetchWithTimeout';

// #CHANGED: Add timeout middleware to client
export const client = createClient<paths>({
  baseUrl: '',
  headers: {
    'Content-Type': 'application/json',
  },
  // #CHANGED: credentials for cookie sending
  credentials: 'include',
});

// #ADDED: Register timeout middleware (30s for all requests)
client.use(createTimeoutMiddleware(30000));

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
  // Auth endpoints (using raw fetch for better cookie control)
  auth: {
    login: async (body: { master_key: string }) => {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        credentials: 'include',  // #CHANGED: Ensure cookies are included
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
        method: 'GET',
        credentials: 'include',  // #CHANGED: Ensure cookies are included
      });
      return res.json();
    },
  },
};