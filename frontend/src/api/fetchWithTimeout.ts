// frontend/src/api/fetchWithTimeout.ts
// ADDED: Utility for fetch with timeout and AbortController

interface FetchWithTimeoutOptions extends RequestInit {
  timeout?: number; // milliseconds, default 30000
}

export class TimeoutError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'TimeoutError';
  }
}

export async function fetchWithTimeout(
  url: string,
  options: FetchWithTimeoutOptions = {}
): Promise<Response> {
  const { timeout = 30000, ...fetchOptions } = options;
  
  const controller = new AbortController();
  const timeoutId = setTimeout(() => {
    controller.abort();
  }, timeout);

  try {
    const response = await fetch(url, {
      ...fetchOptions,
      signal: controller.signal,
    });
    return response;
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') {
      throw new TimeoutError(`Request timeout after ${timeout}ms: ${url}`);
    }
    throw error;
  } finally {
    clearTimeout(timeoutId);
  }
}

// ADDED: Helper for openapi-fetch client
export function createTimeoutMiddleware(timeout: number = 30000) {
  return {
    onRequest({ request }: { request: Request }) {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => {
        controller.abort();
      }, timeout);
      
      // Store timeoutId on request for cleanup
      (request as any)._timeoutId = timeoutId;
      (request as any)._controller = controller;
      
      return request;
    },
    onResponse({ request, response }: { request: Request; response: Response }) {
      // Cleanup timeout
      if ((request as any)._timeoutId) {
        clearTimeout((request as any)._timeoutId);
      }
      return response;
    },
  };
}