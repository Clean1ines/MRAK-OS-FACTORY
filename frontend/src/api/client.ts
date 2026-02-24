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
  credentials: 'include',
});

// #ADDED: Register timeout middleware (30s for all requests)
client.use(createTimeoutMiddleware(30000));

// Authentication now handled via httpOnly cookies set by backend

export const api = {
  projects: {
    // #CHANGED: All endpoints now have 30s timeout via middleware
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
  // Auth endpoints (using raw fetch with timeout)
  auth: {
    login: async (body: { master_key: string }) => {
      const { fetchWithTimeout } = await import('./fetchWithTimeout');
      const res = await fetchWithTimeout('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        credentials: 'include',
        timeout: 30000,
      });
      return res.json();
    },
    logout: async () => {
      const { fetchWithTimeout } = await import('./fetchWithTimeout');
      const res = await fetchWithTimeout('/api/auth/logout', {
        method: 'POST',
        credentials: 'include',
        timeout: 30000,
      });
      return res.json();
    },
    session: async () => {
      const { fetchWithTimeout } = await import('./fetchWithTimeout');
      const res = await fetchWithTimeout('/api/auth/session', {
        credentials: 'include',
        timeout: 30000,
      });
      return res.json();
    },
  },
};