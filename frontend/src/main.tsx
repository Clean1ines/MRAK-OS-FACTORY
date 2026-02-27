import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'react-hot-toast'
import './index.css'
import App from './App.tsx'

const queryClient = new QueryClient({
  defaultOptions: {
    mutations: {
      // Remove unused parameter or disable lint for this line
      onError: () => {
        // Global mutation error handling can be added here if needed
        // Currently we rely on the API client to show toasts
      },
    },
  },
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 5000,
          error: {
            duration: 7000,
          },
        }}
      />
    </QueryClientProvider>
  </StrictMode>,
)
