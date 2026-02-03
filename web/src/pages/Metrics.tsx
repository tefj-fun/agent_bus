import { useState, useEffect } from 'react';
import { PageLayout, PageHeader } from '../components/layout';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { RefreshCw, Cpu, HardDrive, Clock, Activity, CheckCircle, XCircle, Briefcase } from 'lucide-react';

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
                <div className="p-2 bg-blue-100 rounded-lg">
                  <Cpu className="w-5 h-5 text-blue-600" />
                </div>
                <div>
                  <p className="text-sm text-gray-500">CPU Usage</p>
                  <p className="text-2xl font-semibold text-gray-900">
                    {metrics.system.cpu_percent.toFixed(1)}%
                  </p>
                </div>
              </div>
            </Card>

            <Card>
              <div className="flex items-center gap-3">
                <div className="p-2 bg-purple-100 rounded-lg">
                  <HardDrive className="w-5 h-5 text-purple-600" />
                </div>
                <div>
                  <p className="text-sm text-gray-500">Memory</p>
                  <p className="text-2xl font-semibold text-gray-900">
                    {metrics.system.memory_percent.toFixed(1)}%
                  </p>
                  <p className="text-xs text-gray-400">
                    {formatBytes(metrics.system.memory_used_bytes)} / {formatBytes(metrics.system.memory_total_bytes)}
                  </p>
                </div>
              </div>
            </Card>

            <Card>
              <div className="flex items-center gap-3">
                <div className="p-2 bg-green-100 rounded-lg">
                  <Clock className="w-5 h-5 text-green-600" />
                </div>
                <div>
                  <p className="text-sm text-gray-500">Uptime</p>
                  <p className="text-2xl font-semibold text-gray-900">
                    {formatUptime(metrics.system.uptime_seconds)}
                  </p>
                </div>
              </div>
            </Card>

            <Card>
              <div className="flex items-center gap-3">
                <div className="p-2 bg-orange-100 rounded-lg">
                  <Activity className="w-5 h-5 text-orange-600" />
                </div>
                <div>
                  <p className="text-sm text-gray-500">Requests</p>
                  <p className="text-2xl font-semibold text-gray-900">
                    {metrics.counters.requests_total}
                  </p>
                </div>
              </div>
            </Card>
          </div>

          {/* Request Stats */}
          <Card>
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Request Statistics</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="flex items-center gap-3">
                <Activity className="w-5 h-5 text-gray-400" />
                <div>
                  <p className="text-sm text-gray-500">Total Requests</p>
                  <p className="text-xl font-semibold">{metrics.counters.requests_total}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <CheckCircle className="w-5 h-5 text-green-500" />
                <div>
                  <p className="text-sm text-gray-500">Successful</p>
                  <p className="text-xl font-semibold text-green-600">{metrics.counters.requests_success}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <XCircle className="w-5 h-5 text-red-500" />
                <div>
                  <p className="text-sm text-gray-500">Errors</p>
                  <p className="text-xl font-semibold text-red-600">{metrics.counters.requests_error}</p>
                </div>
              </div>
            </div>
          </Card>

          {/* Job Stats */}
          <Card>
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Job Statistics</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="flex items-center gap-3">
                <Briefcase className="w-5 h-5 text-blue-500" />
                <div>
                  <p className="text-sm text-gray-500">Jobs Submitted</p>
                  <p className="text-xl font-semibold">{metrics.counters.jobs_submitted}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <CheckCircle className="w-5 h-5 text-green-500" />
                <div>
                  <p className="text-sm text-gray-500">Completed</p>
                  <p className="text-xl font-semibold text-green-600">{metrics.counters.jobs_completed}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <XCircle className="w-5 h-5 text-red-500" />
                <div>
                  <p className="text-sm text-gray-500">Failed</p>
                  <p className="text-xl font-semibold text-red-600">{metrics.counters.jobs_failed}</p>
                </div>
              </div>
            </div>
          </Card>

          {/* Task Stats */}
          <Card>
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Task Execution</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div>
                <p className="text-sm text-gray-500">Total Tasks</p>
                <p className="text-xl font-semibold">{metrics.counters.tasks_executed}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">GPU Tasks</p>
                <p className="text-xl font-semibold">{metrics.counters.gpu_tasks_executed}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">CPU Tasks</p>
                <p className="text-xl font-semibold">{metrics.counters.cpu_tasks_executed}</p>
              </div>
            </div>
          </Card>

          {/* Last Updated */}
          {lastUpdated && (
            <p className="text-sm text-gray-400 text-center">
              Last updated: {lastUpdated.toLocaleTimeString()}
            </p>
          )}
        </div>
      )}

      {/* Loading state */}
      {loading && !metrics && (
        <Card className="text-center py-12">
          <RefreshCw className="w-8 h-8 text-gray-300 mx-auto mb-4 animate-spin" />
          <p className="text-gray-500">Loading metrics...</p>
        </Card>
      )}
    </PageLayout>
  );
}
