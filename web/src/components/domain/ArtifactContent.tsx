import type { ArtifactType } from '../../types';
import { Card } from '../ui/Card';
import { PlanRenderer } from './PlanRenderer';
import { MarkdownRenderer } from './MarkdownRenderer';
import { ArchitectureRenderer } from './ArchitectureRenderer';
import { UIUXRenderer } from './UIUXRenderer';
import { DevelopmentRenderer } from './DevelopmentRenderer';
import { QARenderer } from './QARenderer';
import { SecurityRenderer } from './SecurityRenderer';
import { MermaidDiagram } from './MermaidDiagram';
import { JsonInspector } from './JsonInspector';
import { parseArtifactJson } from './artifactParsing';

const MARKDOWN_TYPES: ArtifactType[] = [
  'prd',
  'documentation',
  'support',
  'pm_review',
  'delivery',
  'project_plan',
];

export function isMarkdownArtifactType(type: ArtifactType): boolean {
  return MARKDOWN_TYPES.includes(type);
}

export function supportsA4View(type: ArtifactType): boolean {
  return isMarkdownArtifactType(type);
}

export function ArtifactContent({
  type,
  content,
  a4View = true,
}: {
  type: ArtifactType;
  content: string;
  a4View?: boolean;
}) {
  if (type === 'plan') return <PlanRenderer content={content} />;
  if (type === 'architecture') return <ArchitectureRenderer content={content} />;
  if (type === 'uiux') return <UIUXRenderer content={content} />;
  if (type === 'development') return <DevelopmentRenderer content={content} />;
  if (type === 'qa') return <QARenderer content={content} />;
  if (type === 'security') return <SecurityRenderer content={content} />;
  if (type === 'feature_tree_graph') {
    return <MermaidDiagram chart={content} />;
  }

  if (isMarkdownArtifactType(type)) {
    return (
      <div className="doc-shell">
        <div className={`doc-page ${a4View ? 'doc-page--a4' : ''}`}>
          <MarkdownRenderer content={content} />
        </div>
      </div>
    );
  }

  const parsed = parseArtifactJson(content);
  if (parsed.data) {
    return (
      <Card className="p-4">
        <JsonInspector data={parsed.data as unknown as Record<string, unknown>} />
      </Card>
    );
  }

  return (
    <div className="doc-shell">
      <div className={`doc-page ${a4View ? 'doc-page--a4' : ''}`}>
        <MarkdownRenderer content={parsed.raw || content} />
      </div>
    </div>
  );
}
