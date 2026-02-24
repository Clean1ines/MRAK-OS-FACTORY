// frontend/src/api/client.ts
import createClient from 'openapi-fetch';
import type { paths, components } from './generated/schema';
import { createTimeoutMiddleware } from './fetchWithTimeout';

// Get token from sessionStorage
const getSessionToken = () => sessionStorage.getItem('mrak_session_token');

// Create client
export const client = createClient<paths>({
  baseUrl: '',
  headers: {
    'Content-Type': 'application/json',
  },
});

// #ADDED: Register middleware AFTER creating client
client.use({
  onRequest({ request }) {
    const token = getSessionToken();
    if (token) {
      request.headers.set('Authorization', `Bearer ${token}`);
    }
    return request;
  },
});

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
  auth: {
    login: async (body: { master_key: string }) => {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (data.session_token) {
        sessionStorage.setItem('mrak_session_token', data.session_token);
      }
      return data;
    },
    logout: async () => {
      sessionStorage.removeItem('mrak_session_token');
      const res = await fetch('/api/auth/logout', {
        method: 'POST',
      });
      return res.json();
    },
    session: async () => {
      const res = await fetch('/api/auth/session', {
        method: 'GET',
      });
      return res.json();
    },
  },
};