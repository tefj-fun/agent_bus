import { useState, useEffect, useCallback } from 'react';
import { useParams, Link, useLocation } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { PageLayout, PageHeader } from '../components/layout';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { SkeletonWorkflow, SkeletonText } from '../components/ui/Skeleton';
import { WorkflowProgress } from '../components/domain/WorkflowProgress';
import { ActivityFeed } from '../components/domain/ActivityFeed';
import { useJob, useArtifacts, useRestartJob, useCancelJob, useJobUsage } from '../hooks/useProject';
import { useEventStream } from '../hooks/useEventStream';
import { formatDuration, formatRelativeTime, formatCompactNumber, formatCurrencyUSD } from '../utils/utils';
import {
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle,
  Download,
  Eye,
  Wifi,
  WifiOff,
} from 'lucide-react';
import type { WorkflowStage } from '../types';

export function ProjectStatus() {
  const { jobId } = useParams<{ jobId: string }>();
  const location = useLocation();
  const queryClient = useQueryClient();
  const { data: job, isLoading: jobLoading, error: jobError } = useJob(jobId);
  const { data: artifactsData } = useArtifacts(jobId);
  const { data: usageData } = useJobUsage(jobId);
  const restartMutation = useRestartJob();
  const cancelMutation = useCancelJob();

  // Live timer state
  const [elapsed, setElapsed] = useState<number | null>(null);
  const [requirementsExpanded, setRequirementsExpanded] = useState(false);

  // Refresh job data when events arrive
  const handleEvent = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['job', jobId] });
    queryClient.invalidateQueries({ queryKey: ['artifacts', jobId] });
    queryClient.invalidateQueries({ queryKey: ['job-usage', jobId] });
  }, [queryClient, jobId]);

  const { events, connected, error: sseError } = useEventStream({
    jobId,
    onEvent: handleEvent,
  });

  const isCompleted = job?.status === 'completed';
  const isFailed = job?.status === 'failed' || job?.status === 'canceled';
  const isWaitingApproval = job?.status === 'waiting_for_approval';
  const isActive = !isCompleted && !isFailed;
  const isLiveRunning = isActive && !isWaitingApproval;
  const usage = usageData?.usage;
  const currentPath = `${location.pathname}${location.search}`;
  const returnPath = (location.state as { from?: string } | null)?.from;
  const backLink = returnPath
    ? { href: returnPath, label: 'Back' }
    : { href: '/', label: 'Back to Dashboard' };
  const requirements =
    typeof (job?.metadata as Record<string, unknown> | undefined)?.requirements === 'string'
      ? (job?.metadata as Record<string, unknown>).requirements as string
      : '';
  const hasRequirements = requirements.trim().length > 0;
  const isLongRequirements = requirements.length > 500;

  const currentStage = (job?.stage || 'initialization') as WorkflowStage;
  const failureReason = getFailureReason(job?.metadata, events);
  const failedStageId = getFailedStageId(job?.metadata);
  const stageForProgress = (isFailed && failedStageId ? failedStageId : currentStage) as WorkflowStage;
  const failureStage = getFailureStage(stageForProgress);
  const latestTask = (job?.metadata as Record<string, unknown> | undefined)?.['latest_task'] as
    | { task_type?: string; status?: string }
    | undefined;
  const currentStageOverride = latestTask?.task_type === stageForProgress && latestTask?.status === 'completed'
    ? 'completed'
    : undefined;

  const getArtifactRoute = (type: string): string => {
    if (type === 'prd') return `/prd/${jobId}`;
    if (type === 'feature_tree') return `/project/${jobId}/feature-tree`;
    return `/project/${jobId}/artifact/${type}`;
  };

  // Live timer effect
  useEffect(() => {
    if (!job?.created_at) {
      setElapsed(null);
      return;
    }

    const restartAt =
      typeof job?.metadata?.restarted_at === 'string'
        ? job.metadata.restarted_at
        : undefined;
    const start = new Date(restartAt || job.created_at || job.updated_at).getTime();
    const serverNow = new Date(job.updated_at || restartAt || job.created_at).getTime();
    const clientStart = Date.now();
    const baseElapsed = Math.max(0, Math.round((serverNow - start) / 1000));

    const updateElapsed = () => {
      if (isCompleted || isFailed) {
        // Use updated_at for completed/failed jobs
        const end = job.updated_at ? new Date(job.updated_at).getTime() : Date.now();
        setElapsed(Math.max(0, Math.round((end - start) / 1000)));
      } else if (isWaitingApproval) {
        // Freeze while waiting for HITL approval.
        setElapsed(baseElapsed);
      } else {
        // Live timer for running jobs
        const liveElapsed = baseElapsed + Math.floor((Date.now() - clientStart) / 1000);
        setElapsed(Math.max(0, liveElapsed));
      }
    };

    updateElapsed();

    // Only run interval for actively running jobs (not waiting for approval)
    if (isLiveRunning) {
      const interval = setInterval(updateElapsed, 1000);
      return () => clearInterval(interval);
    }
  }, [job?.created_at, job?.updated_at, isCompleted, isFailed, isWaitingApproval, isLiveRunning, isActive]);

  if (jobLoading) {
    return (
      <PageLayout>
        <PageHeader title="Loading..." backLink={{ href: '/', label: 'Back to Dashboard' }} />
        <Card>
          <SkeletonWorkflow />
          <div className="mt-6">
            <SkeletonText lines={5} />
          </div>
        </Card>
      </PageLayout>
    );
  }

  if (jobError || !job) {
    return (
      <PageLayout>
        <PageHeader title="Project Not Found" backLink={{ href: '/', label: 'Back to Dashboard' }} />
        <Card className="text-center py-12">
          <XCircle className="w-12 h-12 text-text-muted mx-auto mb-4" />
          <p className="text-text-secondary mb-4">Could not load project details</p>
          <Link to="/">
            <Button variant="outline">Return to Dashboard</Button>
          </Link>
        </Card>
      </PageLayout>
    );
  }

  return (
    <PageLayout>
      <PageHeader
        title={job.project_id}
        description={
          <div className="flex items-center gap-3 mt-1">
            <StatusBadge status={job.status} />
            {elapsed !== null && (
              <span className="text-sm text-text-secondary">
                {isCompleted || isFailed ? 'Total time' : 'Elapsed'}: {formatDuration(elapsed)}
              </span>
            )}
            {usage && (
              <span className="text-sm text-text-secondary">
                Tokens: {formatCompactNumber(usage.total_tokens)}
                {usage.cost_available ? ` · Cost: ${formatCurrencyUSD(usage.cost_usd)}` : ' · Cost: —'}
              </span>
            )}
          </div>
        }
        backLink={backLink}
        actions={
          <div className="flex items-center gap-2">
            {/* SSE Connection Status */}
            <div className="flex items-center gap-1 text-sm">
              {connected ? (
                <>
                  <Wifi className="w-4 h-4 text-success-500" />
                  <span className="text-success-600">Live</span>
                </>
              ) : (
                <>
                  <WifiOff className="w-4 h-4 text-text-muted" />
                  <span className="text-text-muted">Offline</span>
                </>
              )}
            </div>

            {isActive && (
              <Button
                variant="outline"
                onClick={() => {
                  if (!jobId) return;
                  if (!confirm('Stop this job? This will cancel the workflow.')) return;
                  cancelMutation.mutate({ jobId });
                }}
                loading={cancelMutation.isPending}
              >
                Stop
              </Button>
            )}

            {isCompleted && (
              <Link to={`/project/${jobId}/deliverables`} state={{ from: currentPath }}>
                <Button icon={<Download className="w-4 h-4" />}>
                  View Deliverables
                </Button>
              </Link>
            )}
          </div>
        }
      />

      {/* SSE Error Banner */}
      {sseError && (
        <Card variant="outlined" className="mb-4 border-warning-200 bg-warning-50">
          <div className="flex items-center gap-2 text-warning-700">
            <AlertCircle className="w-5 h-5" />
            <span>{sseError}</span>
          </div>
        </Card>
      )}

      {/* Waiting for Approval Banner */}
      {isWaitingApproval && (
        <Card variant="elevated" className="mb-6 border-warning-200 bg-warning-50">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <AlertCircle className="w-6 h-6 text-warning-600" />
              <div>
                <p className="font-medium text-warning-800">PRD Ready for Review</p>
                <p className="text-sm text-warning-600">
                  Review and approve the PRD to continue the pipeline
                </p>
              </div>
            </div>
            <Link to={`/prd/${jobId}`} state={{ from: currentPath }}>
              <Button>Review PRD</Button>
            </Link>
          </div>
        </Card>
      )}

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          {hasRequirements && (
            <Card>
              <div className="flex items-start justify-between gap-4 mb-3">
                <div>
                  <h3 className="font-semibold text-text-primary">Input Requirements</h3>
                  <p className="text-xs text-text-muted">
                    Original request
                    {job.created_at ? ` · ${formatRelativeTime(job.created_at)}` : ''}
                  </p>
                </div>
                {isLongRequirements && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setRequirementsExpanded((prev) => !prev)}
                  >
                    {requirementsExpanded ? 'Collapse' : 'Show Full'}
                  </Button>
                )}
              </div>
              <div
                className={`rounded-md border border-border bg-bg-secondary p-3 ${
                  requirementsExpanded ? '' : 'max-h-40 overflow-hidden'
                }`}
              >
                <pre className="whitespace-pre-wrap text-sm text-text-secondary">
                  {requirements}
                </pre>
              </div>
            </Card>
          )}

          {/* Workflow Progress */}
          <Card>
            <h3 className="font-semibold text-text-primary mb-4">Workflow Progress</h3>
            <WorkflowProgress
              currentStage={stageForProgress}
              failedStage={isFailed ? stageForProgress : undefined}
              currentStageOverride={currentStageOverride}
            />

            {/* Current Stage Details */}
            {!isCompleted && !isFailed && (
              <div className="mt-6 pt-6 border-t border-border">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-primary-100 flex items-center justify-center animate-pulse">
                    <Clock className="w-5 h-5 text-primary-600" />
                  </div>
                  <div>
                    <p className="font-medium text-text-primary">
                      {stageForProgress.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                    </p>
                    <p className="text-sm text-text-secondary">
                      {isWaitingApproval ? 'Waiting for your approval' : 'In progress...'}
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Completed State */}
            {isCompleted && (
              <div className="mt-6 pt-6 border-t border-border">
                <div className="flex items-center gap-3 text-success-600">
                  <CheckCircle className="w-6 h-6" />
                  <div>
                    <p className="font-medium">All stages completed</p>
                    <p className="text-sm text-text-secondary">
                      Completed {formatRelativeTime(job.updated_at)}
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Failed State */}
            {isFailed && (
              <div className="mt-6 pt-6 border-t border-border">
                <div className="flex items-center gap-3 text-error-600">
                  <XCircle className="w-6 h-6" />
                  <div>
                    <p className="font-medium">
                      {job.status === 'canceled' ? 'Pipeline canceled' : `Pipeline failed at ${failureStage}`}
                    </p>
                    <p className="text-sm text-text-secondary">
                      {failureReason || (job.status === 'canceled'
                        ? 'Canceled by user'
                        : 'Check the activity feed for error details')}
                    </p>
                  </div>
                </div>
                <div className="mt-4 flex items-center gap-2">
                  <Button
                    variant="outline"
                    onClick={() => jobId && restartMutation.mutate(jobId)}
                    loading={restartMutation.isPending}
                  >
                    Restart Workflow
                  </Button>
                </div>
              </div>
            )}
          </Card>

          {/* Completed Artifacts */}
          {artifactsData?.artifacts && artifactsData.artifacts.length > 0 && (
            <Card>
              <h3 className="font-semibold text-text-primary mb-4">Completed Artifacts</h3>
              <div className="space-y-2">
                {artifactsData.artifacts
                  .filter((artifact) => artifact.artifact_type !== 'feature_tree_graph')
                  .map((artifact) => (
                  <div
                    key={artifact.artifact_id}
                    className="flex items-center justify-between p-3 bg-bg-secondary rounded-lg"
                  >
                    <div className="flex items-center gap-3">
                      <CheckCircle className="w-5 h-5 text-success-500" />
                      <span className="font-medium text-text-primary">
                        {artifact.artifact_type.replace(/_/g, ' ').toUpperCase()}
                      </span>
                      <span className="text-sm text-text-secondary">
                        {formatRelativeTime(artifact.created_at)}
                      </span>
                    </div>
                    <Link
                      to={getArtifactRoute(artifact.artifact_type)}
                      state={{ from: currentPath }}
                    >
                      <Button variant="ghost" size="sm" icon={<Eye className="w-4 h-4" />}>
                        View
                      </Button>
                    </Link>
                  </div>
                ))}
              </div>
            </Card>
          )}
        </div>

        {/* Activity Feed Sidebar */}
        <div className="lg:col-span-1">
          <Card>
            <h3 className="font-semibold text-text-primary mb-4">Activity Feed</h3>
            <ActivityFeed events={events} maxItems={8} />
          </Card>
        </div>
      </div>
    </PageLayout>
  );
}

function StatusBadge({ status }: { status: string }) {
  const variants: Record<
    string,
    { variant: 'success' | 'warning' | 'error' | 'info' | 'default'; dot: boolean; pulse: boolean }
  > = {
    queued: { variant: 'default', dot: true, pulse: false },
    running: { variant: 'info', dot: true, pulse: true },
    in_progress: { variant: 'info', dot: true, pulse: true },
    waiting_for_approval: { variant: 'warning', dot: true, pulse: true },
    changes_requested: { variant: 'warning', dot: true, pulse: false },
    completed: { variant: 'success', dot: false, pulse: false },
    failed: { variant: 'error', dot: false, pulse: false },
    canceled: { variant: 'error', dot: false, pulse: false },
  };

  const config = variants[status] || { variant: 'default' as const, dot: false, pulse: false };

  return (
    <Badge variant={config.variant} dot={config.dot} pulse={config.pulse}>
      {status.replace(/_/g, ' ')}
    </Badge>
  );
}

function getFailureReason(
  metadata: Record<string, unknown> | undefined,
  events: { type: string; message: string; metadata?: Record<string, unknown> }[]
): string | null {
  if (metadata) {
    const metaError = metadata.error || metadata.failure_reason || metadata.reason;
    if (typeof metaError === 'string' && metaError.trim().length > 0) {
      return metaError;
    }
  }

  const failedEvent = events.find((event) =>
    event.type === 'job_failed' || event.type === 'task_failed' || event.type === 'failed'
  );
  if (failedEvent?.metadata) {
    const eventError = failedEvent.metadata.error || failedEvent.metadata.reason;
    if (typeof eventError === 'string' && eventError.trim().length > 0) {
      return eventError;
    }
  }
  if (failedEvent?.message && failedEvent.message.toLowerCase().includes('failed')) {
    return failedEvent.message;
  }
  return null;
}

function getFailureStage(
  fallbackStage: WorkflowStage
): string {
  if (fallbackStage && fallbackStage !== 'failed') {
    return fallbackStage.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  }
  return 'unknown stage';
}

function getFailedStageId(metadata: Record<string, unknown> | undefined): WorkflowStage | null {
  const metaStage = metadata?.failed_stage;
  if (typeof metaStage === 'string' && metaStage.trim().length > 0) {
    return metaStage as WorkflowStage;
  }
  return null;
}
