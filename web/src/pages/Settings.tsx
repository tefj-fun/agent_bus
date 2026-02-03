import { useQuery } from '@tanstack/react-query';
import { PageLayout, PageHeader } from '../components/layout';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';

type StorageInfo = {
  backend?: string;
  output_dir?: string | null;
  total_jobs?: number;
  output_dir_exists?: boolean;
  initialized?: boolean;
};

export function Settings() {
  const { data: health, isLoading: healthLoading, error: healthError } = useQuery({
    queryKey: ['health'],
    queryFn: () => fetch('/health').then((res) => res.json()),
    refetchInterval: 10000,
  });

  const {
    data: storageInfo,
    isLoading: storageLoading,
    error: storageError,
  } = useQuery({
    queryKey: ['storage-info'],
    queryFn: async () => {
      const res = await fetch('/api/artifacts/storage/info');
      if (!res.ok) {
        throw new Error('Failed to load storage info');
      }
      return (await res.json()) as StorageInfo;
    },
    refetchInterval: 10000,
  });

  const sseBase = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  const healthStatus =
    healthLoading ? 'loading' : healthError ? 'error' : health?.status || 'unknown';

  return (
    <PageLayout>
      <PageHeader
        title="Settings"
        description="Environment and runtime configuration"
      />

      <div className="grid gap-6">
        <Card>
          <h3 className="font-semibold text-gray-900 mb-3">Backend Status</h3>
          <div className="flex items-center gap-3">
            <Badge
              variant={
                healthStatus === 'healthy'
                  ? 'success'
                  : healthStatus === 'loading'
                  ? 'info'
                  : 'error'
              }
            >
              {healthStatus}
            </Badge>
            <span className="text-sm text-gray-600">API: `/health`</span>
          </div>
        </Card>

        <Card>
          <h3 className="font-semibold text-gray-900 mb-3">Artifacts Storage</h3>
          {storageLoading && <p className="text-sm text-gray-500">Loading...</p>}
          {storageError && (
            <p className="text-sm text-error-600">Failed to load storage info</p>
          )}
          {!storageLoading && !storageError && (
            <dl className="grid md:grid-cols-2 gap-4 text-sm">
              <div>
                <dt className="text-gray-500">Backend</dt>
                <dd className="font-medium text-gray-900">
                  {storageInfo?.backend || 'unknown'}
                </dd>
              </div>
              <div>
                <dt className="text-gray-500">Output Dir</dt>
                <dd className="font-medium text-gray-900">
                  {storageInfo?.output_dir ?? 'n/a'}
                </dd>
              </div>
              <div>
                <dt className="text-gray-500">Jobs With Artifacts</dt>
                <dd className="font-medium text-gray-900">
                  {storageInfo?.total_jobs ?? 0}
                </dd>
              </div>
              <div>
                <dt className="text-gray-500">Output Dir Exists</dt>
                <dd className="font-medium text-gray-900">
                  {storageInfo?.output_dir_exists ? 'yes' : 'no'}
                </dd>
              </div>
            </dl>
          )}
        </Card>

        <Card>
          <h3 className="font-semibold text-gray-900 mb-3">Client Config</h3>
          <dl className="grid md:grid-cols-2 gap-4 text-sm">
            <div>
              <dt className="text-gray-500">API Base</dt>
              <dd className="font-medium text-gray-900">/api (same origin)</dd>
            </div>
            <div>
              <dt className="text-gray-500">SSE Base</dt>
              <dd className="font-medium text-gray-900">{sseBase}</dd>
            </div>
          </dl>
        </Card>

        <Card>
          <h3 className="font-semibold text-gray-900 mb-3">Server Config</h3>
          <p className="text-sm text-gray-600">
            To change LLM models, token limits, or timeouts, edit
            <span className="font-mono"> D:\Python\agent_bus\.env </span>
            and restart Docker:
          </p>
          <pre className="mt-3 text-sm bg-gray-50 rounded-lg p-3">
docker compose down
docker compose up -d
          </pre>
        </Card>
      </div>
    </PageLayout>
  );
}
