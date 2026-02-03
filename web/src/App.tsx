import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ToastProvider } from './components/ui/Toast';
import {
  Dashboard,
  CreateProject,
  PRDReview,
  ProjectStatus,
  Deliverables,
  Memory,
} from './pages';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60, // 1 minute
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <BrowserRouter>
          <Routes>
            {/* Dashboard */}
            <Route path="/" element={<Dashboard />} />

            {/* Create Project */}
            <Route path="/new" element={<CreateProject />} />

            {/* Project Routes */}
            <Route path="/project/:jobId" element={<ProjectStatus />} />
            <Route path="/project/:jobId/deliverables" element={<Deliverables />} />

            {/* PRD Review */}
            <Route path="/prd/:jobId" element={<PRDReview />} />

            {/* Memory */}
            <Route path="/memory" element={<Memory />} />

            {/* Redirects for old UI routes */}
            <Route path="/ui" element={<Navigate to="/" replace />} />
            <Route path="/ui/jobs" element={<Navigate to="/" replace />} />

            {/* 404 */}
            <Route
              path="*"
              element={
                <div className="min-h-screen flex items-center justify-center bg-gray-50">
                  <div className="text-center">
                    <h1 className="text-4xl font-bold text-gray-900 mb-2">404</h1>
                    <p className="text-gray-600 mb-4">Page not found</p>
                    <a
                      href="/"
                      className="text-primary-600 hover:text-primary-700 font-medium"
                    >
                      Return to Dashboard
                    </a>
                  </div>
                </div>
              }
            />
          </Routes>
        </BrowserRouter>
      </ToastProvider>
    </QueryClientProvider>
  );
}

export default App;
