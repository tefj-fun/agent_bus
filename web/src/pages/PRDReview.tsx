import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { PageLayout, PageHeader } from '../components/layout';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Textarea } from '../components/ui/Textarea';
import { Modal, ConfirmDialog } from '../components/ui/Modal';
import { SkeletonText } from '../components/ui/Skeleton';
import { useToast } from '../components/ui/Toast';
import { MemoryHitBadge } from '../components/domain/MemoryHitCard';
import { useJob, usePrd, useApprovePrd, useRequestChanges } from '../hooks/useProject';
import { Copy, Download, Check, AlertTriangle, CheckCircle } from 'lucide-react';

export function PRDReview() {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();
  const { addToast } = useToast();

  const { data: job, isLoading: jobLoading } = useJob(jobId);
  const { data: prd, isLoading: prdLoading, error: prdError } = usePrd(jobId);

  const approveMutation = useApprovePrd(jobId!);
  const requestChangesMutation = useRequestChanges(jobId!);

  const [feedback, setFeedback] = useState('');
  const [showApproveDialog, setShowApproveDialog] = useState(false);
  const [showChangesDialog, setShowChangesDialog] = useState(false);
  const [copied, setCopied] = useState(false);

  const isWaitingApproval = job?.status === 'waiting_for_approval';
  const isLoading = jobLoading || prdLoading;
  const requirements =
    (job?.metadata as Record<string, unknown> | undefined)?.requirements;

  const handleCopy = async () => {
    if (prd?.content) {
      await navigator.clipboard.writeText(prd.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleDownload = () => {
    if (prd?.content) {
      const blob = new Blob([prd.content], { type: 'text/markdown' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `prd-${job?.project_id || jobId}.md`;
      a.click();
      URL.revokeObjectURL(url);
    }
  };

  const handleApprove = async () => {
    try {
      await approveMutation.mutateAsync(feedback || undefined);
      addToast({
        type: 'success',
        title: 'PRD Approved',
        description: 'Document generation pipeline has started',
      });
      setShowApproveDialog(false);
      navigate(`/project/${jobId}`);
    } catch (err) {
      addToast({
        type: 'error',
        title: 'Approval Failed',
        description: err instanceof Error ? err.message : 'Unknown error',
      });
    }
  };

  const handleRequestChanges = async () => {
    if (!feedback.trim()) {
      addToast({
        type: 'warning',
        title: 'Feedback Required',
        description: 'Please provide feedback for the changes',
      });
      return;
    }

    try {
      await requestChangesMutation.mutateAsync(feedback);
      addToast({
        type: 'info',
        title: 'Changes Requested',
        description: 'PRD will be regenerated with your feedback',
      });
      setShowChangesDialog(false);
      setFeedback('');
    } catch (err) {
      addToast({
        type: 'error',
        title: 'Request Failed',
        description: err instanceof Error ? err.message : 'Unknown error',
      });
    }
  };

  return (
    <PageLayout>
      <PageHeader
        title={`PRD: ${job?.project_id || 'Loading...'}`}
        description={
          isWaitingApproval
            ? 'Review the PRD and approve or request changes'
            : `Status: ${job?.status || 'Unknown'}`
        }
        backLink={{ href: `/project/${jobId}`, label: 'Back to Project' }}
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              icon={copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
              onClick={handleCopy}
              disabled={!prd?.content}
            >
              {copied ? 'Copied' : 'Copy'}
            </Button>
            <Button
              variant="ghost"
              size="sm"
              icon={<Download className="w-4 h-4" />}
              onClick={handleDownload}
              disabled={!prd?.content}
            >
              Download
            </Button>
          </div>
        }
      />

      <div className="grid lg:grid-cols-4 gap-6">
        {/* Main Content */}
        <div className="lg:col-span-3">
          <Card>
            {/* Status Banner */}
            {isWaitingApproval && (
              <div className="flex items-center gap-2 mb-4 p-3 bg-warning-50 border border-warning-200 rounded-lg">
                <AlertTriangle className="w-5 h-5 text-warning-600" />
                <span className="text-warning-800 font-medium">
                  This PRD is pending your review
                </span>
              </div>
            )}

            {!isWaitingApproval && job?.status === 'running' && (
              <div className="flex items-center gap-2 mb-4 p-3 bg-primary-50 border border-primary-200 rounded-lg">
                <CheckCircle className="w-5 h-5 text-primary-600" />
                <span className="text-primary-800 font-medium">
                  PRD approved - Pipeline is running
                </span>
              </div>
            )}

            {typeof requirements === 'string' && requirements.trim().length > 0 && (
              <div className="mb-4 p-4 border border-gray-200 rounded-lg bg-white">
                <h4 className="text-sm font-semibold text-gray-900 mb-2">
                  Input Requirements
                </h4>
                <pre className="whitespace-pre-wrap text-sm text-gray-700 bg-gray-50 rounded-md p-3">
                  {requirements}
                </pre>
              </div>
            )}

            {/* PRD Content */}
            {isLoading ? (
              <SkeletonText lines={15} />
            ) : prdError ? (
              <div className="text-center py-8">
                <p className="text-gray-500 mb-2">PRD is not ready yet</p>
                <p className="text-sm text-gray-400">
                  Current stage: {job?.stage?.replace(/_/g, ' ')}
                </p>
              </div>
            ) : (
              <div className="prose prose-sm max-w-none">
                <pre className="whitespace-pre-wrap text-sm text-gray-700 bg-gray-50 rounded-lg p-4 overflow-x-auto font-mono">
                  {prd?.content}
                </pre>
              </div>
            )}
          </Card>

          {/* Actions */}
          {isWaitingApproval && prd?.content && (
            <Card className="mt-6">
              <h3 className="font-semibold text-gray-900 mb-4">Your Decision</h3>

              <Textarea
                label="Feedback (optional for approval, required for changes)"
                placeholder="Add notes for the team or revision instructions..."
                value={feedback}
                onChange={(e) => setFeedback(e.target.value)}
                className="min-h-[100px]"
              />

              <div className="flex items-center justify-between mt-4 pt-4 border-t border-gray-200">
                <Button
                  variant="outline"
                  onClick={() => setShowChangesDialog(true)}
                  icon={<AlertTriangle className="w-4 h-4" />}
                >
                  Request Changes
                </Button>
                <Button
                  variant="primary"
                  onClick={() => setShowApproveDialog(true)}
                  icon={<CheckCircle className="w-4 h-4" />}
                >
                  Approve & Continue Pipeline
                </Button>
              </div>
            </Card>
          )}
        </div>

        {/* Sidebar */}
        <div className="lg:col-span-1 space-y-4">
          {/* Similar Projects */}
          <Card>
            <h3 className="font-semibold text-gray-900 mb-3">Similar Projects</h3>
            {prd?.memory_hits && prd.memory_hits.length > 0 ? (
              <div className="space-y-1">
                {prd.memory_hits.map((hit) => (
                  <MemoryHitBadge
                    key={hit.id}
                    title={hit.id}
                    similarity={hit.score}
                  />
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-500">No similar projects found</p>
            )}
          </Card>

          {/* Quick Info */}
          <Card>
            <h3 className="font-semibold text-gray-900 mb-3">Info</h3>
            <dl className="space-y-2 text-sm">
              <div>
                <dt className="text-gray-500">Project ID</dt>
                <dd className="font-medium text-gray-900">{job?.project_id}</dd>
              </div>
              <div>
                <dt className="text-gray-500">Status</dt>
                <dd>
                  <Badge
                    variant={
                      job?.status === 'waiting_for_approval'
                        ? 'warning'
                        : job?.status === 'completed'
                        ? 'success'
                        : 'default'
                    }
                  >
                    {job?.status?.replace(/_/g, ' ')}
                  </Badge>
                </dd>
              </div>
              {prd?.created_at && (
                <div>
                  <dt className="text-gray-500">Generated</dt>
                  <dd className="text-gray-700">
                    {new Date(prd.created_at).toLocaleString()}
                  </dd>
                </div>
              )}
            </dl>
          </Card>
        </div>
      </div>

      {/* Approve Confirmation Dialog */}
      <Modal
        isOpen={showApproveDialog}
        onClose={() => setShowApproveDialog(false)}
        title="Approve PRD?"
        size="md"
        footer={
          <>
            <Button variant="outline" onClick={() => setShowApproveDialog(false)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              onClick={handleApprove}
              loading={approveMutation.isPending}
            >
              Yes, Approve & Start
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <p className="text-gray-600">
            This will start the full document generation pipeline:
          </p>
          <ol className="list-decimal list-inside space-y-1 text-sm text-gray-600">
            <li>Plan Generation (~5 min)</li>
            <li>Architecture Design (~10 min)</li>
            <li>UI/UX Design (~5 min)</li>
            <li>Development Plan (~15 min)</li>
            <li>QA + Security + Docs (~10 min parallel)</li>
            <li>PM Review + Delivery (~5 min)</li>
          </ol>
          <p className="text-sm text-gray-500 mt-4">
            Estimated total: 45-60 minutes
          </p>
        </div>
      </Modal>

      {/* Request Changes Dialog */}
      <ConfirmDialog
        isOpen={showChangesDialog}
        onClose={() => setShowChangesDialog(false)}
        onConfirm={handleRequestChanges}
        title="Request Changes?"
        message="The PRD will be regenerated with your feedback. Make sure you've provided clear instructions."
        confirmText="Request Changes"
        variant="warning"
        loading={requestChangesMutation.isPending}
      />
    </PageLayout>
  );
}
