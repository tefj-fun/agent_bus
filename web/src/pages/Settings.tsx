import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { PageLayout, PageHeader } from '../components/layout';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Textarea } from '../components/ui/Textarea';

type StorageInfo = {
  backend?: string;
  output_dir?: string | null;
  total_jobs?: number;
  output_dir_exists?: boolean;
  initialized?: boolean;
};

type RuntimeSettings = {
  llm_mode: string;
  llm_provider: string;
  anthropic_model: string;
  openai_model: string;
  anthropic_max_tokens: number;
  prd_max_tokens: number;
  timeout_llm_call: number;
  timeout_task_completion: number;
  timeout_db_query: number;
  timeout_redis_operation: number;
  anthropic_api_key_masked?: string | null;
  openai_api_key_masked?: string | null;
};

export function Settings() {
  const queryClient = useQueryClient();
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

  const {
    data: runtimeSettings,
    isLoading: settingsLoading,
    error: settingsError,
  } = useQuery({
    queryKey: ['runtime-settings'],
    queryFn: async () => {
      const res = await fetch('/api/settings');
      if (!res.ok) {
        throw new Error('Failed to load settings');
      }
      return (await res.json()) as RuntimeSettings;
    },
    refetchInterval: false,
  });

  const [settingsForm, setSettingsForm] = useState({
    llm_mode: '',
    llm_provider: '',
    anthropic_model: '',
    openai_model: '',
    anthropic_max_tokens: '',
    prd_max_tokens: '',
    timeout_llm_call: '',
    timeout_task_completion: '',
    timeout_db_query: '',
    timeout_redis_operation: '',
    anthropic_api_key: '',
    openai_api_key: '',
  });

  useEffect(() => {
    if (!runtimeSettings) return;
    setSettingsForm((prev) => ({
      ...prev,
      llm_mode: runtimeSettings.llm_mode,
      llm_provider: runtimeSettings.llm_provider,
      anthropic_model: runtimeSettings.anthropic_model,
      openai_model: runtimeSettings.openai_model,
      anthropic_max_tokens: String(runtimeSettings.anthropic_max_tokens),
      prd_max_tokens: String(runtimeSettings.prd_max_tokens),
      timeout_llm_call: String(runtimeSettings.timeout_llm_call),
      timeout_task_completion: String(runtimeSettings.timeout_task_completion),
      timeout_db_query: String(runtimeSettings.timeout_db_query),
      timeout_redis_operation: String(runtimeSettings.timeout_redis_operation),
    }));
  }, [runtimeSettings]);

  const updateSettings = useMutation({
    mutationFn: async () => {
      const payload: Record<string, unknown> = {
        llm_mode: settingsForm.llm_mode,
        llm_provider: settingsForm.llm_provider,
        anthropic_model: settingsForm.anthropic_model,
        openai_model: settingsForm.openai_model,
        anthropic_max_tokens: Number(settingsForm.anthropic_max_tokens),
        prd_max_tokens: Number(settingsForm.prd_max_tokens),
        timeout_llm_call: Number(settingsForm.timeout_llm_call),
        timeout_task_completion: Number(settingsForm.timeout_task_completion),
        timeout_db_query: Number(settingsForm.timeout_db_query),
        timeout_redis_operation: Number(settingsForm.timeout_redis_operation),
      };
      if (settingsForm.anthropic_api_key.trim().length > 0) {
        payload.anthropic_api_key = settingsForm.anthropic_api_key.trim();
      }
      if (settingsForm.openai_api_key.trim().length > 0) {
        payload.openai_api_key = settingsForm.openai_api_key.trim();
      }

      const res = await fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        throw new Error('Failed to update settings');
      }
      return (await res.json()) as RuntimeSettings;
    },
    onSuccess: () => {
      setSettingsForm((prev) => ({
        ...prev,
        anthropic_api_key: '',
        openai_api_key: '',
      }));
      queryClient.invalidateQueries({ queryKey: ['runtime-settings'] });
    },
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
          <h3 className="font-semibold text-text-primary mb-3">Backend Status</h3>
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
            <span className="text-sm text-text-secondary">API: `/health`</span>
          </div>
        </Card>

        <Card>
          <h3 className="font-semibold text-text-primary mb-3">Artifacts Storage</h3>
          {storageLoading && <p className="text-sm text-text-secondary">Loading...</p>}
          {storageError && (
            <p className="text-sm text-error-600">Failed to load storage info</p>
          )}
          {!storageLoading && !storageError && (
            <dl className="grid md:grid-cols-2 gap-4 text-sm">
              <div>
                <dt className="text-text-secondary">Backend</dt>
                <dd className="font-medium text-text-primary">
                  {storageInfo?.backend || 'unknown'}
                </dd>
              </div>
              <div>
                <dt className="text-text-secondary">Output Dir</dt>
                <dd className="font-medium text-text-primary">
                  {storageInfo?.output_dir ?? 'n/a'}
                </dd>
              </div>
              <div>
                <dt className="text-text-secondary">Jobs With Artifacts</dt>
                <dd className="font-medium text-text-primary">
                  {storageInfo?.total_jobs ?? 0}
                </dd>
              </div>
              <div>
                <dt className="text-text-secondary">Output Dir Exists</dt>
                <dd className="font-medium text-text-primary">
                  {storageInfo?.output_dir_exists ? 'yes' : 'no'}
                </dd>
              </div>
            </dl>
          )}
        </Card>

        <Card>
          <h3 className="font-semibold text-text-primary mb-3">Client Config</h3>
          <dl className="grid md:grid-cols-2 gap-4 text-sm">
            <div>
              <dt className="text-text-secondary">API Base</dt>
              <dd className="font-medium text-text-primary">/api (same origin)</dd>
            </div>
            <div>
              <dt className="text-text-secondary">SSE Base</dt>
              <dd className="font-medium text-text-primary">{sseBase}</dd>
            </div>
          </dl>
        </Card>

        <Card>
          <h3 className="font-semibold text-text-primary mb-3">Server Config</h3>
          {settingsLoading && <p className="text-sm text-text-secondary">Loading settings...</p>}
          {settingsError && (
            <p className="text-sm text-error-600">Failed to load runtime settings</p>
          )}
          {!settingsLoading && !settingsError && (
            <div className="space-y-4">
              <p className="text-sm text-text-secondary">
                Changes apply immediately for new requests. Secrets are write-only and masked
                below.
              </p>
              <div className="grid md:grid-cols-2 gap-4 text-sm">
                <label className="flex flex-col gap-1">
                  <span className="text-text-secondary">LLM Mode</span>
                  <input
                    className="border border-border bg-bg-primary text-text-primary rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500"
                    value={settingsForm.llm_mode}
                    onChange={(e) => setSettingsForm({ ...settingsForm, llm_mode: e.target.value })}
                  />
                </label>
                <label className="flex flex-col gap-1">
                  <span className="text-text-secondary">LLM Provider</span>
                  <input
                    className="border border-border bg-bg-primary text-text-primary rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500"
                    value={settingsForm.llm_provider}
                    onChange={(e) =>
                      setSettingsForm({ ...settingsForm, llm_provider: e.target.value })
                    }
                  />
                </label>
                <label className="flex flex-col gap-1">
                  <span className="text-text-secondary">Anthropic Model</span>
                  <input
                    className="border border-border bg-bg-primary text-text-primary rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500"
                    value={settingsForm.anthropic_model}
                    onChange={(e) =>
                      setSettingsForm({ ...settingsForm, anthropic_model: e.target.value })
                    }
                  />
                </label>
                <label className="flex flex-col gap-1">
                  <span className="text-text-secondary">OpenAI Model</span>
                  <input
                    className="border border-border bg-bg-primary text-text-primary rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500"
                    value={settingsForm.openai_model}
                    onChange={(e) =>
                      setSettingsForm({ ...settingsForm, openai_model: e.target.value })
                    }
                  />
                </label>
                <label className="flex flex-col gap-1">
                  <span className="text-text-secondary">Anthropic Max Tokens</span>
                  <input
                    className="border border-border bg-bg-primary text-text-primary rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500"
                    type="number"
                    min={1}
                    value={settingsForm.anthropic_max_tokens}
                    onChange={(e) =>
                      setSettingsForm({ ...settingsForm, anthropic_max_tokens: e.target.value })
                    }
                  />
                </label>
                <label className="flex flex-col gap-1">
                  <span className="text-text-secondary">PRD Max Tokens</span>
                  <input
                    className="border border-border bg-bg-primary text-text-primary rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500"
                    type="number"
                    min={1}
                    value={settingsForm.prd_max_tokens}
                    onChange={(e) =>
                      setSettingsForm({ ...settingsForm, prd_max_tokens: e.target.value })
                    }
                  />
                </label>
                <label className="flex flex-col gap-1">
                  <span className="text-text-secondary">LLM Timeout (s)</span>
                  <input
                    className="border border-border bg-bg-primary text-text-primary rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500"
                    type="number"
                    min={1}
                    value={settingsForm.timeout_llm_call}
                    onChange={(e) =>
                      setSettingsForm({ ...settingsForm, timeout_llm_call: e.target.value })
                    }
                  />
                </label>
                <label className="flex flex-col gap-1">
                  <span className="text-text-secondary">Task Timeout (s)</span>
                  <input
                    className="border border-border bg-bg-primary text-text-primary rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500"
                    type="number"
                    min={1}
                    value={settingsForm.timeout_task_completion}
                    onChange={(e) =>
                      setSettingsForm({
                        ...settingsForm,
                        timeout_task_completion: e.target.value,
                      })
                    }
                  />
                </label>
                <label className="flex flex-col gap-1">
                  <span className="text-text-secondary">DB Timeout (s)</span>
                  <input
                    className="border border-border bg-bg-primary text-text-primary rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500"
                    type="number"
                    min={1}
                    value={settingsForm.timeout_db_query}
                    onChange={(e) =>
                      setSettingsForm({ ...settingsForm, timeout_db_query: e.target.value })
                    }
                  />
                </label>
                <label className="flex flex-col gap-1">
                  <span className="text-text-secondary">Redis Timeout (s)</span>
                  <input
                    className="border border-border bg-bg-primary text-text-primary rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500"
                    type="number"
                    min={1}
                    value={settingsForm.timeout_redis_operation}
                    onChange={(e) =>
                      setSettingsForm({ ...settingsForm, timeout_redis_operation: e.target.value })
                    }
                  />
                </label>
              </div>

              <div className="grid md:grid-cols-2 gap-4 text-sm">
                <label className="flex flex-col gap-1">
                  <span className="text-text-secondary">
                    Anthropic API Key (current: {runtimeSettings?.anthropic_api_key_masked || 'unset'})
                  </span>
                  <Textarea
                    className="min-h-[80px]"
                    placeholder="Paste new key to update"
                    value={settingsForm.anthropic_api_key}
                    onChange={(e) =>
                      setSettingsForm({ ...settingsForm, anthropic_api_key: e.target.value })
                    }
                  />
                </label>
                <label className="flex flex-col gap-1">
                  <span className="text-text-secondary">
                    OpenAI API Key (current: {runtimeSettings?.openai_api_key_masked || 'unset'})
                  </span>
                  <Textarea
                    className="min-h-[80px]"
                    placeholder="Paste new key to update"
                    value={settingsForm.openai_api_key}
                    onChange={(e) =>
                      setSettingsForm({ ...settingsForm, openai_api_key: e.target.value })
                    }
                  />
                </label>
              </div>

              <div className="flex items-center gap-3">
                <Button
                  variant="primary"
                  onClick={() => updateSettings.mutate()}
                  loading={updateSettings.isPending}
                >
                  Save Settings
                </Button>
                {updateSettings.isError && (
                  <span className="text-sm text-error-600">Failed to update settings</span>
                )}
                {updateSettings.isSuccess && (
                  <span className="text-sm text-success-600">Settings updated</span>
                )}
              </div>
            </div>
          )}
        </Card>
      </div>
    </PageLayout>
  );
}
