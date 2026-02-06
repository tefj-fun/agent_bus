import { useState } from 'react';
import { Link } from 'react-router-dom';
import { PageLayout, PageHeader } from '../components/layout';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { SkeletonCard } from '../components/ui/Skeleton';
import { useJobs, useDeleteJob, useRestartJob } from '../hooks/useProject';
import { formatRelativeTime } from '../utils/utils';
import { Plus, AlertCircle, Clock, CheckCircle, XCircle, ArrowRight, Trash2 } from 'lucide-react';
import type { Job } from '../types';

export function Dashboard() {
  const { data, isLoading, error } = useJobs();
  const deleteJob = useDeleteJob();
  const restartJob = useRestartJob();
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [restartingId, setRestartingId] = useState<string | null>(null);

  const handleDelete = async (jobId: string, projectId: string) => {
    if (!confirm(`Delete project "${projectId}"? This cannot be undone.`)) {
      return;
    }
    setDeletingId(jobId);
    try {
      await deleteJob.mutateAsync(jobId);
    } finally {
      setDeletingId(null);
    }
  };

  const handleRestart = async (jobId: string, projectId: string) => {
    if (!confirm(`Restart failed project "${projectId}" from the beginning?`)) {
      return;
    }
    setRestartingId(jobId);
    try {
      await restartJob.mutateAsync(jobId);
    } finally {
      setRestartingId(null);
    }
  };

  const jobs = data?.jobs || [];

  // Categorize jobs
  const pendingReview = jobs.filter(j => j.status === 'waiting_for_approval');
  const activeJobs = jobs.filter(
    j =>
      j.status === 'running' ||
      j.status === 'queued' ||
      j.status === 'in_progress' ||
      j.status === 'changes_requested'
  );
  const completedJobs = jobs.filter(j => j.status === 'completed').slice(0, 5);
  const failedJobs = jobs.filter(j => j.status === 'failed').slice(0, 3);

  // Stats
  const totalCompleted = jobs.filter(j => j.status === 'completed').length;
  const successRate = jobs.length > 0
    ? Math.round((totalCompleted / jobs.length) * 100)
    : 0;

  return (
    <PageLayout>
      <PageHeader
        title="Dashboard"
        description="Transform customer requirements into comprehensive planning documents"
        actions={
          <Link to="/new">
            <Button icon={<Plus className="w-4 h-4" />}>
              Create Project
            </Button>
          </Link>
        }
      />

      {/* Quick Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <StatCard
          label="Active Projects"
          value={activeJobs.length}
          icon={<Clock className="w-5 h-5 text-primary-500" />}
        />
        <StatCard
          label="Pending Review"
          value={pendingReview.length}
          icon={<AlertCircle className="w-5 h-5 text-warning-500" />}
          highlight={pendingReview.length > 0}
        />
        <StatCard
          label="Completed"
          value={totalCompleted}
          icon={<CheckCircle className="w-5 h-5 text-success-500" />}
        />
        <StatCard
          label="Success Rate"
          value={`${successRate}%`}
          icon={<CheckCircle className="w-5 h-5 text-success-500" />}
        />
      </div>

      {/* Error State */}
      {error && (
        <Card variant="outlined" className="mb-6 border-error-200 bg-error-50">
          <div className="flex items-center gap-3 text-error-700">
            <XCircle className="w-5 h-5" />
            <span>Failed to load projects. Please try again.</span>
            <Button variant="outline" size="sm" onClick={() => window.location.reload()}>
              Retry
            </Button>
          </div>
        </Card>
      )}

      {/* Pending Review Section */}
      {pendingReview.length > 0 && (
        <section className="mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-3 flex items-center gap-2">
            <AlertCircle className="w-5 h-5 text-warning-500" />
            Pending Your Review
          </h2>
          <div className="space-y-2">
            {pendingReview.map(job => (
              <Card key={job.job_id} variant="outlined" className="border-warning-200 bg-warning-50/50">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Badge variant="warning" dot pulse>
                      PRD Ready
                    </Badge>
                    <span className="font-medium text-gray-900">{job.project_id}</span>
                    <span className="text-sm text-gray-500">
                      {formatRelativeTime(job.updated_at)}
                    </span>
                  </div>
                  <Link to={`/prd/${job.job_id}`}>
                    <Button size="sm">
                      Review PRD
                      <ArrowRight className="w-4 h-4 ml-1" />
                    </Button>
                  </Link>
                </div>
              </Card>
            ))}
          </div>
        </section>
      )}

      {/* Active Projects */}
      <section className="mb-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-3">
          Active Projects
        </h2>
        {isLoading ? (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[1, 2, 3].map(i => <SkeletonCard key={i} />)}
          </div>
        ) : activeJobs.length > 0 ? (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {activeJobs.map(job => (
              <ProjectCard key={job.job_id} job={job} />
            ))}
          </div>
        ) : (
          <Card variant="outlined" className="text-center py-8">
            <p className="text-gray-500 mb-4">No active projects</p>
            <Link to="/new">
              <Button variant="outline" icon={<Plus className="w-4 h-4" />}>
                Create your first project
              </Button>
            </Link>
          </Card>
        )}
      </section>

      {/* Recent Completed */}
      {completedJobs.length > 0 && (
        <section className="mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-3">
            Recent Completed
          </h2>
          <div className="space-y-2">
            {completedJobs.map(job => (
              <Card key={job.job_id} variant="outlined">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <CheckCircle className="w-5 h-5 text-success-500" />
                    <span className="font-medium text-gray-900">{job.project_id}</span>
                    <span className="text-sm text-gray-500">
                      Completed {formatRelativeTime(job.updated_at)}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Link to={`/project/${job.job_id}/deliverables`}>
                      <Button variant="ghost" size="sm">
                        View Artifacts
                      </Button>
                    </Link>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDelete(job.job_id, job.project_id)}
                      disabled={deletingId === job.job_id}
                      className="text-gray-400 hover:text-error-600 hover:bg-error-50"
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </section>
      )}

      {/* Failed Jobs */}
      {failedJobs.length > 0 && (
        <section>
          <h2 className="text-lg font-semibold text-gray-900 mb-3 flex items-center gap-2">
            <XCircle className="w-5 h-5 text-error-500" />
            Failed Jobs
          </h2>
          <div className="space-y-2">
            {failedJobs.map(job => (
              <Card key={job.job_id} variant="outlined" className="border-error-200">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Badge variant="error">Failed</Badge>
                    <span className="font-medium text-gray-900">{job.project_id}</span>
                    <span className="text-sm text-gray-500">
                      at {getFailureStageLabel(job)}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Link to={`/project/${job.job_id}`}>
                      <Button variant="ghost" size="sm">
                        View Details
                      </Button>
                    </Link>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleRestart(job.job_id, job.project_id)}
                      disabled={restartingId === job.job_id}
                      className="text-error-600 hover:text-error-700 hover:bg-error-50"
                    >
                      Restart
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDelete(job.job_id, job.project_id)}
                      disabled={deletingId === job.job_id}
                      className="text-error-600 hover:text-error-700 hover:bg-error-50"
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
                {getFailureReasonLabel(job) && (
                  <p className="text-sm text-error-700 mt-2">
                    {getFailureReasonLabel(job)}
                  </p>
                )}
              </Card>
            ))}
          </div>
        </section>
      )}
    </PageLayout>
  );
}

function getFailureReasonLabel(job: Job): string | null {
  const metadata = job.metadata as Record<string, unknown> | undefined;
  if (!metadata) return null;
  const metaError = metadata.error || metadata.failure_reason || metadata.reason;
  if (typeof metaError === 'string' && metaError.trim().length > 0) {
    return metaError;
  }
  return null;
}

function getFailureStageLabel(job: Job): string {
  const metadata = job.metadata as Record<string, unknown> | undefined;
  const metaStage = metadata?.failed_stage;
  if (typeof metaStage === 'string' && metaStage.trim().length > 0) {
    return metaStage.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  }
  if (job.stage && job.stage !== 'failed') {
    return job.stage.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  }
  return 'unknown stage';
}

function StatCard({
  label,
  value,
  icon,
  highlight,
}: {
  label: string;
  value: string | number;
  icon: React.ReactNode;
  highlight?: boolean;
}) {
  return (
    <Card
      variant={highlight ? 'elevated' : 'default'}
      className={highlight ? 'border-warning-200 bg-warning-50' : ''}
    >
      <div className="flex items-center gap-3">
        {icon}
        <div>
          <p className="text-2xl font-bold text-gray-900">{value}</p>
          <p className="text-sm text-gray-500">{label}</p>
        </div>
      </div>
    </Card>
  );
}

function ProjectCard({ job }: { job: Job }) {
  const getStageProgress = (stage: string): number => {
    const stages = [
      'initialization', 'prd_generation', 'waiting_for_approval', 'plan_generation',
      'architecture_design', 'uiux_design', 'development', 'qa_testing',
      'security_review', 'documentation', 'support_docs', 'pm_review', 'delivery', 'completed'
    ];
    const index = stages.indexOf(stage);
    return index >= 0 ? Math.round((index / (stages.length - 1)) * 100) : 0;
  };

  const progress = getStageProgress(job.stage);
  const stageName = job.stage.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());

  return (
    <Link to={`/project/${job.job_id}`}>
      <Card variant="interactive">
        <h3 className="font-medium text-gray-900 mb-2">{job.project_id}</h3>

        {/* Progress bar */}
        <div className="w-full bg-gray-200 rounded-full h-2 mb-2">
          <div
            className="bg-primary-500 h-2 rounded-full transition-all duration-300"
            style={{ width: `${progress}%` }}
          />
        </div>

        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-600">{stageName}</span>
          <span className="text-gray-500">{progress}%</span>
        </div>

        <p className="text-xs text-gray-400 mt-2">
          Started {formatRelativeTime(job.created_at)}
        </p>
      </Card>
    </Link>
  );
}
