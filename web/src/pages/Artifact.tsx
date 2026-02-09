import { useParams, Link, useLocation } from 'react-router-dom';
import { PageLayout, PageHeader } from '../components/layout';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { ArtifactViewer } from '../components/domain/ArtifactViewer';
import { SkeletonText } from '../components/ui/Skeleton';
import { useArtifacts, useJob } from '../hooks/useProject';
import { AlertCircle } from 'lucide-react';
import type { ArtifactType } from '../types';

const ARTIFACT_TYPES: ArtifactType[] = [
  'prd',
  'feature_tree',
  'feature_tree_graph',
  'plan',
  'project_plan',
  'architecture',
  'uiux',
  'development',
  'qa',
  'security',
  'documentation',
  'support',
  'pm_review',
  'delivery',
];

function isArtifactType(value?: string): value is ArtifactType {
  return typeof value === 'string' && ARTIFACT_TYPES.includes(value as ArtifactType);
}

export function Artifact() {
  const { jobId, type } = useParams<{ jobId: string; type: string }>();
  const location = useLocation();
  const { data: job } = useJob(jobId);
  const { data: artifactsData, isLoading } = useArtifacts(jobId);

  const artifactType = isArtifactType(type) ? type : undefined;
  const artifact = artifactType
    ? artifactsData?.artifacts?.find((item) => item.artifact_type === artifactType)
    : undefined;

  if (!jobId || !artifactType) {
    return (
      <PageLayout>
        <PageHeader title="Artifact Not Found" backLink={{ href: '/', label: 'Back to Dashboard' }} />
        <Card className="text-center py-12">
          <AlertCircle className="w-12 h-12 text-text-muted mx-auto mb-4" />
          <p className="text-text-secondary mb-4">Invalid artifact type.</p>
          <Link to="/">
            <Button variant="outline">Return to Dashboard</Button>
          </Link>
        </Card>
      </PageLayout>
    );
  }

  const returnPath = (location.state as { from?: string } | null)?.from;
  const backLink = returnPath
    ? { href: returnPath, label: 'Back' }
    : { href: `/project/${jobId}/deliverables`, label: 'Back to Deliverables' };

  return (
    <PageLayout>
      <PageHeader
        title={job?.project_id || 'Project Artifact'}
        description="Single artifact view"
        backLink={backLink}
      />

      {isLoading && (
        <Card>
          <SkeletonText lines={6} />
        </Card>
      )}

      {!isLoading && !artifact && (
        <Card className="text-center py-12">
          <AlertCircle className="w-12 h-12 text-text-muted mx-auto mb-4" />
          <p className="text-text-secondary mb-4">Artifact not found for this project.</p>
          <Link to={`/project/${jobId}/deliverables`}>
            <Button variant="outline">View All Deliverables</Button>
          </Link>
        </Card>
      )}

      {!isLoading && artifact && (
        <ArtifactViewer
          artifactId={artifact.artifact_id}
          type={artifactType}
          content={artifact.content}
          createdAt={artifact.created_at}
        />
      )}
    </PageLayout>
  );
}
