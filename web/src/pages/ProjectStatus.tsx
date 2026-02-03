import { useParams, Link } from 'react-router-dom';
import { PageLayout, PageHeader } from '../components/layout';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { SkeletonWorkflow, SkeletonText } from '../components/ui/Skeleton';
import { WorkflowProgress } from '../components/domain/WorkflowProgress';
import { ActivityFeed } from '../components/domain/ActivityFeed';
import { useJob, useArtifacts } from '../hooks/useProject';
import { useEventStream } from '../hooks/useEventStream';
import { formatRelativeTime, formatDuration } from '../utils/utils';
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
  const { data: job, isLoading: jobLoading, error: jobError } = useJob(jobId);
  const { data: artifactsData } = useArtifacts(jobId);
  const { events, connected, error: sseError } = useEventStream({ jobId });

  const isCompleted = job?.status === 'completed';
  const isFailed = job?.status === 'failed';
  const isWaitingApproval = job?.status === 'waiting_approval';

  const currentStage = (job?.stage || 'initialization') as WorkflowStage;

  // Calculate elapsed time
  const getElapsedTime = () => {
    if (!job?.created_at) return null;
    const start = new Date(job.created_at).getTime();
    const end = job.updated_at ? new Date(job.updated_at).getTime() : Date.now();
    return Math.round((end - start) / 1000);
  };

  const elapsed = getElapsedTime();

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
          <XCircle className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-600 mb-4">Could not load project details</p>
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
            {elapsed && (
              <span className="text-sm text-gray-500">
                {isCompleted || isFailed ? 'Total time' : 'Elapsed'}: {formatDuration(elapsed)}
              </span>
            )}
          </div>
        }
        backLink={{ href: '/', label: 'Back to Dashboard' }}
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
                  <WifiOff className="w-4 h-4 text-gray-400" />
                  <span className="text-gray-500">Offline</span>
                </>
              )}
            </div>

            {isCompleted && (
              <Link to={`/project/${jobId}/deliverables`}>
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
            <Link to={`/prd/${jobId}`}>
              <Button>Review PRD</Button>
            </Link>
          </div>
        </Card>
      )}

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Workflow Progress */}
          <Card>
            <h3 className="font-semibold text-gray-900 mb-4">Workflow Progress</h3>
            <WorkflowProgress
              currentStage={currentStage}
              failedStage={isFailed ? currentStage : undefined}
            />

            {/* Current Stage Details */}
            {!isCompleted && !isFailed && (
              <div className="mt-6 pt-6 border-t border-gray-200">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-primary-100 flex items-center justify-center animate-pulse">
                    <Clock className="w-5 h-5 text-primary-600" />
                  </div>
                  <div>
                    <p className="font-medium text-gray-900">
                      {currentStage.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                    </p>
                    <p className="text-sm text-gray-500">
                      {isWaitingApproval ? 'Waiting for your approval' : 'In progress...'}
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Completed State */}
            {isCompleted && (
              <div className="mt-6 pt-6 border-t border-gray-200">
                <div className="flex items-center gap-3 text-success-600">
                  <CheckCircle className="w-6 h-6" />
                  <div>
                    <p className="font-medium">All stages completed</p>
                    <p className="text-sm text-gray-500">
                      Completed {formatRelativeTime(job.updated_at)}
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Failed State */}
            {isFailed && (
              <div className="mt-6 pt-6 border-t border-gray-200">
                <div className="flex items-center gap-3 text-error-600">
                  <XCircle className="w-6 h-6" />
                  <div>
                    <p className="font-medium">Pipeline failed at {currentStage.replace(/_/g, ' ')}</p>
                    <p className="text-sm text-gray-500">
                      Check the activity feed for error details
                    </p>
                  </div>
                </div>
              </div>
            )}
          </Card>

          {/* Completed Artifacts */}
          {artifactsData?.artifacts && artifactsData.artifacts.length > 0 && (
            <Card>
              <h3 className="font-semibold text-gray-900 mb-4">Completed Artifacts</h3>
              <div className="space-y-2">
                {artifactsData.artifacts.map((artifact) => (
                  <div
                    key={artifact.artifact_id}
                    className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                  >
                    <div className="flex items-center gap-3">
                      <CheckCircle className="w-5 h-5 text-success-500" />
                      <span className="font-medium text-gray-900">
                        {artifact.artifact_type.replace(/_/g, ' ').toUpperCase()}
                      </span>
                      <span className="text-sm text-gray-500">
                        {formatRelativeTime(artifact.created_at)}
                      </span>
                    </div>
                    <Link
                      to={
                        artifact.artifact_type === 'prd'
                          ? `/prd/${jobId}`
                          : `/project/${jobId}/deliverables`
                      }
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
            <h3 className="font-semibold text-gray-900 mb-4">Activity Feed</h3>
            <ActivityFeed events={events} maxItems={20} />
          </Card>
        </div>
      </div>
    </PageLayout>
  );
}

function StatusBadge({ status }: { status: string }) {
  const variants: Record<string, { variant: 'success' | 'warning' | 'error' | 'info' | 'default'; dot: boolean; pulse: boolean }> = {
    queued: { variant: 'default', dot: true, pulse: false },
    running: { variant: 'info', dot: true, pulse: true },
    waiting_approval: { variant: 'warning', dot: true, pulse: true },
    completed: { variant: 'success', dot: false, pulse: false },
    failed: { variant: 'error', dot: false, pulse: false },
  };

  const config = variants[status] || { variant: 'default' as const, dot: false, pulse: false };

  return (
    <Badge variant={config.variant} dot={config.dot} pulse={config.pulse}>
      {status.replace(/_/g, ' ')}
    </Badge>
  );
}
