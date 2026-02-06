import { useState, useEffect } from 'react';
import { PageLayout, PageHeader } from '../components/layout';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { RefreshCw, Cpu, HardDrive, Clock, Activity, CheckCircle, XCircle, Briefcase } from 'lucide-react';
import { formatCompactNumber, formatCurrencyUSD } from '../utils/utils';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface MetricsData {
  counters: {
    requests_total: number;
    requests_success: number;
    requests_error: number;
    jobs_submitted: number;
    jobs_completed: number;
    jobs_failed: number;
    tasks_executed: number;
    gpu_tasks_executed: number;
    cpu_tasks_executed: number;
  };
  system: {
    cpu_percent: number;
    memory_percent: number;
    memory_used_bytes: number;
    memory_total_bytes: number;
    uptime_seconds: number;
  };
  usage?: {
    input_tokens: number;
    output_tokens: number;
    total_tokens: number;
    calls: number;
    cost_usd: number | null;
    cost_available?: boolean;
  } | null;
  timestamp: number;
}

function formatBytes(bytes: number): string {
  const gb = bytes / (1024 * 1024 * 1024);
  if (gb >= 1) return `${gb.toFixed(1)} GB`;
  const mb = bytes / (1024 * 1024);
  return `${mb.toFixed(0)} MB`;
}

function formatUptime(seconds: number): string {
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const mins = Math.floor((seconds % 3600) / 60);

  if (days > 0) return `${days}d ${hours}h ${mins}m`;
  if (hours > 0) return `${hours}h ${mins}m`;
  return `${mins}m`;
}

export function Metrics() {
  const [metrics, setMetrics] = useState<MetricsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchMetrics = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetch(`${API_BASE}/metrics`);
      if (!res.ok) {
        throw new Error(`Failed to fetch metrics: ${res.status}`);
      }
      const data = await res.json();
      setMetrics(data);
      setLastUpdated(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch metrics');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMetrics();
    const interval = setInterval(fetchMetrics, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, []);

  return (
    <PageLayout>
      <PageHeader
        title="System Metrics"
        description="Monitor system health and performance"
        actions={
          <Button
            onClick={fetchMetrics}
            disabled={loading}
            variant="secondary"
            icon={<RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />}
          >
            Refresh
          </Button>
        }
      />

      {error && (
        <Card variant="outlined" className="mb-6 border-error-200 bg-error-50">
          <p className="text-error-700">{error}</p>
        </Card>
      )}

      {metrics && (
        <div className="space-y-6">
          {/* System Stats */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Card>
              <div className="flex items-center gap-3">
                <div className="p-2 bg-info-100 rounded-lg">
                  <Cpu className="w-5 h-5 text-info-600" />
                </div>
                <div>
                  <p className="text-sm text-text-secondary">CPU Usage</p>
                  <p className="text-2xl font-semibold text-text-primary">
                    {metrics.system.cpu_percent.toFixed(1)}%
                  </p>
                </div>
              </div>
            </Card>

            <Card>
              <div className="flex items-center gap-3">
                <div className="p-2 bg-primary-100 rounded-lg">
                  <HardDrive className="w-5 h-5 text-primary-600" />
                </div>
                <div>
                  <p className="text-sm text-text-secondary">Memory</p>
                  <p className="text-2xl font-semibold text-text-primary">
                    {metrics.system.memory_percent.toFixed(1)}%
                  </p>
                  <p className="text-xs text-text-muted">
                    {formatBytes(metrics.system.memory_used_bytes)} / {formatBytes(metrics.system.memory_total_bytes)}
                  </p>
                </div>
              </div>
            </Card>

            <Card>
              <div className="flex items-center gap-3">
                <div className="p-2 bg-success-100 rounded-lg">
                  <Clock className="w-5 h-5 text-success-600" />
                </div>
                <div>
                  <p className="text-sm text-text-secondary">Uptime</p>
                  <p className="text-2xl font-semibold text-text-primary">
                    {formatUptime(metrics.system.uptime_seconds)}
                  </p>
                </div>
              </div>
            </Card>

            <Card>
              <div className="flex items-center gap-3">
                <div className="p-2 bg-warning-100 rounded-lg">
                  <Activity className="w-5 h-5 text-warning-600" />
                </div>
                <div>
                  <p className="text-sm text-text-secondary">Requests</p>
                  <p className="text-2xl font-semibold text-text-primary">
                    {metrics.counters.requests_total}
                  </p>
                </div>
              </div>
            </Card>
          </div>

          {/* Request Stats */}
          <Card>
            <h3 className="text-lg font-semibold text-text-primary mb-4">Request Statistics</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="flex items-center gap-3">
                <Activity className="w-5 h-5 text-text-muted" />
                <div>
                  <p className="text-sm text-text-secondary">Total Requests</p>
                  <p className="text-xl font-semibold">{metrics.counters.requests_total}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <CheckCircle className="w-5 h-5 text-success-500" />
                <div>
                  <p className="text-sm text-text-secondary">Successful</p>
                  <p className="text-xl font-semibold text-success-600">{metrics.counters.requests_success}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <XCircle className="w-5 h-5 text-error-500" />
                <div>
                  <p className="text-sm text-text-secondary">Errors</p>
                  <p className="text-xl font-semibold text-error-600">{metrics.counters.requests_error}</p>
                </div>
              </div>
            </div>
          </Card>

          {/* Job Stats */}
          <Card>
            <h3 className="text-lg font-semibold text-text-primary mb-4">Job Statistics</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="flex items-center gap-3">
                <Briefcase className="w-5 h-5 text-info-500" />
                <div>
                  <p className="text-sm text-text-secondary">Jobs Submitted</p>
                  <p className="text-xl font-semibold">{metrics.counters.jobs_submitted}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <CheckCircle className="w-5 h-5 text-success-500" />
                <div>
                  <p className="text-sm text-text-secondary">Completed</p>
                  <p className="text-xl font-semibold text-success-600">{metrics.counters.jobs_completed}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <XCircle className="w-5 h-5 text-error-500" />
                <div>
                  <p className="text-sm text-text-secondary">Failed</p>
                  <p className="text-xl font-semibold text-error-600">{metrics.counters.jobs_failed}</p>
                </div>
              </div>
            </div>
          </Card>

          {/* Task Stats */}
          <Card>
            <h3 className="text-lg font-semibold text-text-primary mb-4">Task Execution</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div>
                <p className="text-sm text-text-secondary">Total Tasks</p>
                <p className="text-xl font-semibold">{metrics.counters.tasks_executed}</p>
              </div>
              <div>
                <p className="text-sm text-text-secondary">GPU Tasks</p>
                <p className="text-xl font-semibold">{metrics.counters.gpu_tasks_executed}</p>
              </div>
              <div>
                <p className="text-sm text-text-secondary">CPU Tasks</p>
                <p className="text-xl font-semibold">{metrics.counters.cpu_tasks_executed}</p>
              </div>
            </div>
          </Card>

          {metrics.usage && (
            <Card>
              <h3 className="text-lg font-semibold text-text-primary mb-4">LLM Usage & Cost</h3>
              <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                <div>
                  <p className="text-sm text-text-secondary">Total Tokens</p>
                  <p className="text-xl font-semibold">{formatCompactNumber(metrics.usage.total_tokens)}</p>
                </div>
                <div>
                  <p className="text-sm text-text-secondary">Input Tokens</p>
                  <p className="text-xl font-semibold">{formatCompactNumber(metrics.usage.input_tokens)}</p>
                </div>
                <div>
                  <p className="text-sm text-text-secondary">Output Tokens</p>
                  <p className="text-xl font-semibold">{formatCompactNumber(metrics.usage.output_tokens)}</p>
                </div>
                <div>
                  <p className="text-sm text-text-secondary">Estimated Cost</p>
                  <p className="text-xl font-semibold">
                    {metrics.usage.cost_available ? formatCurrencyUSD(metrics.usage.cost_usd) : '—'}
                  </p>
                </div>
              </div>
              <p className="text-xs text-text-muted mt-3">
                {metrics.usage.cost_available
                  ? `Based on ${metrics.usage.calls} LLM calls.`
                  : `Pricing not configured. ${metrics.usage.calls} LLM calls tracked.`}
              </p>
            </Card>
          )}

          {/* Last Updated */}
          {lastUpdated && (
            <p className="text-sm text-text-muted text-center">
              Last updated: {lastUpdated.toLocaleTimeString()}
            </p>
          )}
        </div>
      )}

      {/* Loading state */}
      {loading && !metrics && (
        <Card className="text-center py-12">
          <RefreshCw className="w-8 h-8 text-text-muted mx-auto mb-4 animate-spin" />
          <p className="text-text-secondary">Loading metrics...</p>
        </Card>
      )}
    </PageLayout>
  );
}
