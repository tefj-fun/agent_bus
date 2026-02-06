import { useParams, Link } from 'react-router-dom';
import { PageLayout, PageHeader } from '../components/layout';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { SkeletonCard } from '../components/ui/Skeleton';
import { useToast } from '../components/ui/Toast';
import { ArtifactCard } from '../components/domain/ArtifactViewer';
import { useJob, useArtifacts } from '../hooks/useProject';
import { api } from '../api/client';
import { formatRelativeTime } from '../utils/utils';
import { Download, Package, CheckCircle, AlertCircle } from 'lucide-react';
import { useState } from 'react';
import type { ArtifactType } from '../types';

export function Deliverables() {
  const { jobId } = useParams<{ jobId: string }>();
  const { addToast } = useToast();
  const { data: job, isLoading: jobLoading } = useJob(jobId);
  const { data: artifactsData, isLoading: artifactsLoading } = useArtifacts(jobId);

  const [downloading, setDownloading] = useState(false);
  const [viewingArtifact, setViewingArtifact] = useState<string | null>(null);
  const [a4View, setA4View] = useState(true);
  const [viewMode, setViewMode] = useState<'markdown' | 'pdf'>('markdown');

  const isLoading = jobLoading || artifactsLoading;
  const artifacts = artifactsData?.artifacts || [];
  const isCompleted = job?.status === 'completed';

  // Group artifacts by category
  const planningDocs = artifacts.filter(a => ['prd', 'plan'].includes(a.artifact_type));
  const technicalDocs = artifacts.filter(a => ['architecture', 'uiux', 'development'].includes(a.artifact_type));
  const qualityDocs = artifacts.filter(a => ['qa', 'security', 'documentation', 'support'].includes(a.artifact_type));

  const handleDownloadAll = async () => {
    if (!jobId) return;

    setDownloading(true);
    try {
      const blob = await api.exportProject(jobId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${job?.project_id || jobId}-deliverables.zip`;
      a.click();
      URL.revokeObjectURL(url);

      addToast({
        type: 'success',
        title: 'Download Started',
        description: 'Your deliverables ZIP is downloading',
      });
    } catch (err) {
      addToast({
        type: 'error',
        title: 'Download Failed',
        description: err instanceof Error ? err.message : 'Unknown error',
      });
    } finally {
      setDownloading(false);
    }
  };

  const handleDownloadArtifact = (artifact: { artifact_type: string; content: string }) => {
    const blob = new Blob([artifact.content], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${artifact.artifact_type}-${job?.project_id || jobId}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const getArtifactRoute = (type: string): string => {
    if (type === 'prd') return `/prd/${jobId}`;
    return `/project/${jobId}/artifact/${type}`;
  };

  return (
    <PageLayout>
      <PageHeader
        title="Project Deliverables"
        description={
          <div className="flex items-center gap-2 mt-1">
            <span className="text-gray-600">{job?.project_id}</span>
            {isCompleted && (
              <Badge variant="success" size="sm">
                <CheckCircle className="w-3 h-3 mr-1" />
                Completed {formatRelativeTime(job?.updated_at || '')}
              </Badge>
            )}
          </div>
        }
        backLink={{ href: `/project/${jobId}`, label: 'Back to Project' }}
      />

      {/* Download All Banner */}
      <Card variant="elevated" className="mb-6 bg-gradient-to-r from-primary-50 to-primary-100 border-primary-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-full bg-primary-200 flex items-center justify-center">
              <Package className="w-6 h-6 text-primary-700" />
            </div>
            <div>
              <p className="font-semibold text-primary-900">
                {artifacts.length} Documents Ready
              </p>
              <p className="text-sm text-primary-700">
                All planning documents for AI coding agents
              </p>
            </div>
          </div>
          <Button
            size="lg"
            icon={<Download className="w-5 h-5" />}
            onClick={handleDownloadAll}
            loading={downloading}
            disabled={artifacts.length === 0}
          >
            Download All as ZIP
          </Button>
        </div>
      </Card>

      {/* Loading State */}
      {isLoading && (
        <div className="grid md:grid-cols-2 gap-4">
          {[1, 2, 3, 4].map(i => <SkeletonCard key={i} />)}
        </div>
      )}

      {/* No Artifacts State */}
      {!isLoading && artifacts.length === 0 && (
        <Card className="text-center py-12">
          <AlertCircle className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-600 mb-2">No deliverables available yet</p>
          <p className="text-sm text-gray-500 mb-4">
            Documents are generated as the pipeline progresses
          </p>
          <Link to={`/project/${jobId}`}>
            <Button variant="outline">Check Pipeline Status</Button>
          </Link>
        </Card>
      )}

      {/* Artifacts Grid */}
      {!isLoading && artifacts.length > 0 && (
        <div className="space-y-8">
          {/* Planning Documents */}
          {planningDocs.length > 0 && (
            <section>
              <h2 className="text-lg font-semibold text-gray-900 mb-4">
                Planning Documents
              </h2>
              <div className="grid md:grid-cols-2 gap-4">
                {planningDocs.map((artifact) => (
                  <ArtifactCard
                    key={artifact.artifact_id}
                    type={artifact.artifact_type as ArtifactType}
                    createdAt={artifact.created_at}
                    size={artifact.content.length}
                    onView={() => window.location.href = getArtifactRoute(artifact.artifact_type)}
                    onDownload={() => handleDownloadArtifact(artifact)}
                  />
                ))}
              </div>
            </section>
          )}

          {/* Technical Documents */}
          {technicalDocs.length > 0 && (
            <section>
              <h2 className="text-lg font-semibold text-gray-900 mb-4">
                Technical Documents
              </h2>
              <div className="grid md:grid-cols-2 gap-4">
                {technicalDocs.map((artifact) => (
                  <ArtifactCard
                    key={artifact.artifact_id}
                    type={artifact.artifact_type as ArtifactType}
                    createdAt={artifact.created_at}
                    size={artifact.content.length}
                    onView={() => setViewingArtifact(artifact.artifact_id)}
                    onDownload={() => handleDownloadArtifact(artifact)}
                  />
                ))}
              </div>
            </section>
          )}

          {/* Quality & Support */}
          {qualityDocs.length > 0 && (
            <section>
              <h2 className="text-lg font-semibold text-gray-900 mb-4">
                Quality & Support
              </h2>
              <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
                {qualityDocs.map((artifact) => (
                  <ArtifactCard
                    key={artifact.artifact_id}
                    type={artifact.artifact_type as ArtifactType}
                    createdAt={artifact.created_at}
                    size={artifact.content.length}
                    onView={() => setViewingArtifact(artifact.artifact_id)}
                    onDownload={() => handleDownloadArtifact(artifact)}
                  />
                ))}
              </div>
            </section>
          )}
        </div>
      )}

      {/* Artifact Viewer Modal */}
      {viewingArtifact && (
        <div
          className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4"
          onClick={() => {
            setViewingArtifact(null);
            setA4View(true);
            setViewMode('markdown');
          }}
        >
          <Card
            className="max-w-4xl w-full max-h-[80vh] overflow-auto"
            onClick={(e) => e.stopPropagation()}
          >
            {(() => {
              const artifact = artifacts.find(a => a.artifact_id === viewingArtifact);
              if (!artifact) return null;
              return (
                <>
                  <div className="flex items-center justify-between mb-4 pb-4 border-b border-gray-200">
                    <h2 className="text-lg font-semibold">
                      {artifact.artifact_type.replace(/_/g, ' ').toUpperCase()}
                    </h2>
                    <div className="flex items-center gap-2">
                      <Button
                        variant={viewMode === 'markdown' ? 'primary' : 'outline'}
                        size="sm"
                        onClick={() => setViewMode('markdown')}
                      >
                        Markdown
                      </Button>
                      <Button
                        variant={viewMode === 'pdf' ? 'primary' : 'outline'}
                        size="sm"
                        onClick={() => setViewMode('pdf')}
                      >
                        PDF Preview
                      </Button>
                      <Button
                        variant={a4View ? 'primary' : 'outline'}
                        size="sm"
                        onClick={() => setA4View((prev) => !prev)}
                        disabled={viewMode === 'pdf'}
                      >
                        {a4View ? 'A4 View On' : 'A4 View Off'}
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        icon={<Download className="w-4 h-4" />}
                        onClick={() => handleDownloadArtifact(artifact)}
                      >
                        Download
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          setViewingArtifact(null);
                          setA4View(true);
                          setViewMode('markdown');
                        }}
                      >
                        Close
                      </Button>
                    </div>
                  </div>
                  {viewMode === 'pdf' ? (
                    <div className="doc-shell">
                      <div className="doc-page doc-page--a4 doc-page--pdf">
                        <iframe
                          title="PDF preview"
                          src={(() => {
                            const url = new URL(
                              `/api/artifacts/pdf/${artifact.artifact_id}`,
                              window.location.origin
                            );
                            url.searchParams.set('ts', String(Date.now()));
                            return url.toString();
                          })()}
                          className="w-full h-[80vh] border-0"
                        />
                      </div>
                    </div>
                  ) : (
                    <div className="doc-shell">
                      <div className={`doc-page ${a4View ? 'doc-page--a4' : ''}`}>
                        <pre className="doc-markdown">{artifact.content}</pre>
                      </div>
                    </div>
                  )}
                </>
              );
            })()}
          </Card>
        </div>
      )}
    </PageLayout>
  );
}
