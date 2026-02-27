import createClient from 'openapi-fetch';
import toast from 'react-hot-toast';
import type { paths, components } from './generated/schema';
import { createTimeoutMiddleware } from './fetchWithTimeout';

// Extend Window interface for deduplication
declare global {
  interface Window {
    __lastToast: string | null;
  }
}

// ---------- Augment OpenAPI schema with auth endpoints (not generated) ----------
declare module './generated/schema' {
  interface paths {
    '/api/auth/login': {
      post: {
        requestBody: {
          content: {
            'application/json': { master_key: string };
          };
        };
        responses: {
          200: {
            content: {
              'application/json': { session_token: string } | { status: string };
            };
          };
        };
      };
    };
    '/api/auth/logout': {
      post: {
        responses: {
          200: {
            content: {
              'application/json': { status: string };
            };
          };
        };
      };
    };
    '/api/auth/session': {
      get: {
        responses: {
          200: {
            content: {
              'application/json': { authenticated: boolean; expires_at?: string };
            };
          };
        };
      };
    };
  }
}

// ---------- Types ----------
type ErrorResponse = components['schemas']['Error']; // { error?: string }

// ---------- Token Management ----------
/**
 * Retrieves the authentication token from sessionStorage.
 * @returns {string | null} The token or null if not present.
 */
const getSessionToken = (): string | null => {
  return sessionStorage.getItem('mrak_session_token');
};

/**
 * Stores the authentication token in sessionStorage.
 * @param {string} token - The token to store.
 */
const setSessionToken = (token: string): void => {
  sessionStorage.setItem('mrak_session_token', token);
};

/**
 * Removes the authentication token from sessionStorage.
 */
const clearSessionToken = (): void => {
  sessionStorage.removeItem('mrak_session_token');
};

// ---------- Error Message Extraction ----------
/**
 * Extracts a user-friendly error message from an unknown error.
 * @param {unknown} error - The error object (could be API error, Error instance, etc.)
 * @returns {string} A human-readable error message.
 */
const getErrorMessage = (error: unknown): string => {
  // If it's an API error response (from openapi-fetch)
  if (error && typeof error === 'object' && 'error' in error) {
    const apiError = error as ErrorResponse;
    return apiError.error || 'Произошла неизвестная ошибка';
  }
  // If it's a standard Error instance
  if (error instanceof Error) {
    return error.message;
  }
  // Fallback
  return 'Произошла неизвестная ошибка';
};

// ---------- Toast Helpers ----------
/**
 * Shows a user-friendly error toast with deduplication to avoid spam in development.
 * @param {string} message - The message to display.
 */
const showErrorToast = (message: string): void => {
  // Простая дедупликация для разработки (убирает дубли в StrictMode)
  const key = `error-${message}`;
  if (window.__lastToast === key) return;
  window.__lastToast = key;
  setTimeout(() => {
    window.__lastToast = null;
  }, 1000);
  toast.error(message);
};

// ---------- API Client Setup ----------
/**
 * Unified API client with automatic Bearer token injection,
 * 401 redirect handling, and user-friendly error toasts.
 */
export const client = createClient<paths>({
  baseUrl: '',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request middleware: adds Bearer token if available
client.use({
  onRequest({ request }) {
    const token = getSessionToken();
    console.log('[API Request]', request.method, request.url, token ? 'with token' : 'no token'); // Debug
    if (token) {
      request.headers.set('Authorization', `Bearer ${token}`);
    }
    return request;
  },
});

// Response middleware: handles errors and 401
client.use({
  onResponse({ response }) {
    console.log('[API Response]', response.status, response.url); // Debug

    // If response is not ok (status >= 400)
    if (!response.ok) {
      // Special handling for 401 Unauthorized
      if (response.status === 401) {
        clearSessionToken();
        // Redirect to login page (full page reload)
        window.location.href = '/login';
        // Return a dummy response to stop further processing (openapi-fetch will treat it as error)
        return new Response(JSON.stringify({ error: 'Сессия истекла' }), {
          status: 401,
          headers: { 'Content-Type': 'application/json' },
        });
      }

      // For other errors, try to parse error message
      return response
        .clone()
        .json()
        .then((errData) => {
          const message = getErrorMessage(errData);
          showErrorToast(message);
          return response; // Return original response so openapi-fetch can still populate error
        })
        .catch(() => {
          // If parsing fails, show generic message
          // #CHANGED: friendlier message for 5xx errors
          let message: string;
          if (response.status >= 500 && response.status < 600) {
            message = 'Сервер временно недоступен. Пожалуйста, попробуйте позже.';
          } else {
            message = `Ошибка ${response.status}: ${response.statusText}`;
          }
          showErrorToast(message);
          return response;
        });
    }
    return response;
  },
});

// Add timeout middleware (assuming it exists)
client.use(createTimeoutMiddleware(30000));

// ---------- Typed API Endpoints ----------
/**
 * Predefined API methods for common resources.
 * All methods return `{ data, error }` as per openapi-fetch.
 */
export const api = {
  projects: {
    /**
     * Fetches the list of all projects.
     * @returns {Promise<{ data?: components['schemas']['Project'][], error?: ErrorResponse }>}
     */
    list: () => client.GET('/api/projects'),

    /**
     * Creates a new project.
     * @param {components['schemas']['ProjectCreate']} body - Project data.
     * @returns {Promise<{ data?: { id: string, name: string }, error?: ErrorResponse }>}
     */
    create: (body: components['schemas']['ProjectCreate']) =>
      client.POST('/api/projects', { body }),

    /**
     * Deletes a project by ID.
     * @param {string} projectId - UUID of the project.
     * @returns {Promise<{ data?: { status: string }, error?: ErrorResponse }>}
     */
    delete: (projectId: string) =>
      client.DELETE('/api/projects/{project_id}', { params: { path: { project_id: projectId } } }),
  },

  models: {
    /**
     * Fetches the list of available LLM models.
     * @returns {Promise<{ data?: { id: string }[], error?: ErrorResponse }>}
     */
    list: () => client.GET('/api/models'),
  },

  modes: {
    /**
     * Fetches the list of available prompt modes.
     * @returns {Promise<{ data?: { id: string, name: string, default?: boolean }[], error?: ErrorResponse }>}
     */
    list: () => client.GET('/api/modes'),
  },

  artifactTypes: {
    /**
     * Fetches the list of artifact types.
     * @returns {Promise<{ data?: components['schemas']['ArtifactType'][], error?: ErrorResponse }>}
     */
    list: () => client.GET('/api/artifact-types'),
  },

  artifacts: {
    /**
     * Fetches artifacts for a given project.
     * @param {string} projectId - UUID of the project.
     * @returns {Promise<{ data?: components['schemas']['Artifact'][], error?: ErrorResponse }>}
     */
    list: (projectId: string) =>
      client.GET('/api/projects/{project_id}/artifacts', { params: { path: { project_id: projectId } } }),
  },

  messages: {
    /**
     * Fetches message history (LLMResponse artifacts) for a project.
     * @param {string} projectId - UUID of the project.
     * @returns {Promise<{ data?: components['schemas']['Artifact'][], error?: ErrorResponse }>}
     */
    list: (projectId: string) =>
      client.GET('/api/projects/{project_id}/messages', { params: { path: { project_id: projectId } } }),
  },

  auth: {
    /**
     * Authenticates with master key.
     * On success, stores the session token in sessionStorage.
     * @param {Object} body - { master_key: string }
     * @returns {Promise<any>} Server response (contains session_token on success).
     */
    login: async (body: { master_key: string }) => {
      try {
        const res = await fetch('/api/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        });
        const data = await res.json();
        console.log('[Login] Response:', data); // Debug
        if (!res.ok) {
          // Если статус не 2xx, показываем тост
          const message = getErrorMessage(data) || `Ошибка входа (${res.status})`;
          showErrorToast(message);
          throw new Error(message);
        }
        if (data.session_token) {
          setSessionToken(data.session_token);
        }
        return data;
      } catch (error) {
        // Если fetch упал (сетевая ошибка)
        const message = error instanceof Error ? error.message : 'Ошибка соединения с сервером';
        showErrorToast(message);
        throw error;
      }
    },

    /**
     * Logs out the current user.
     * Removes token locally and calls logout endpoint.
     */
    logout: async () => {
      try {
        const res = await fetch('/api/auth/logout', {
          method: 'POST',
        });
        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          const message = getErrorMessage(data) || `Ошибка выхода (${res.status})`;
          showErrorToast(message);
        }
        clearSessionToken();
        return await res.json().catch(() => ({}));
      } catch (error) {
        const message = error instanceof Error ? error.message : 'Ошибка соединения с сервером';
        showErrorToast(message);
        clearSessionToken(); // Всё равно чистим токен локально
        throw error;
      }
    },

    /**
     * Checks current session status.
     * Uses the authenticated client (automatically adds token and handles errors).
     * @returns {Promise<{ data?: { authenticated: boolean; expires_at?: string }, error?: ErrorResponse }>}
     */
    session: async () => {
      return client.GET('/api/auth/session', {});
    },
  },
};
