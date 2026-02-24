import createClient from 'openapi-fetch';
import type { paths, components } from './generated/schema';

export const client = createClient<paths>({
  baseUrl: '',  // БЫЛО: '/api' → СТАЛО: ''
  headers: {
    'Content-Type': 'application/json',
  },
});

export const setAuthToken = (token: string | null) => {
  if (token) {
    client.use({
      onRequest({ request }) {
        request.headers.set('X-Master-Key', token);
        return request;
      },
    });
  }
};

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
};