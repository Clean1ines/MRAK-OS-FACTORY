import createClient from 'openapi-fetch';
import type { paths, components } from './generated/schema';

// Пустая строка = текущий origin (прокси Vite)
const baseUrl = import.meta.env.VITE_API_URL || '';

export const client = createClient<paths>({
baseUrl,
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

// Типизированные вспомогательные функции
export const api = {
projects: {
list: () => client.GET('/api/projects'),
create: (body: components['schemas']['ProjectCreate']) =>
client.POST('/api/projects', { body }),
delete: (projectId: string) =>
client.DELETE('/api/projects/{project_id}', { params: { path: { project_id: projectId } } }),
},
};
