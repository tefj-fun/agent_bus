import { useMemo, useState, useEffect, useCallback } from 'react';
import type { ReactNode } from 'react';
import { useParams, Link, useLocation } from 'react-router-dom';
import { PageLayout, PageHeader } from '../components/layout';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { MermaidDiagram } from '../components/domain/MermaidDiagram';
import { PdfPreview } from '../components/domain/PdfPreview';
import { useArtifacts, useJob } from '../hooks/useProject';
import { formatRelativeTime } from '../utils/utils';
import { AlertCircle, Layers, GitBranch, Box } from 'lucide-react';
import type { Artifact } from '../types';

type FeatureNode = {
  id?: string;
  name?: string;
  description?: string;
  module_id?: string;
  reuse_decision?: string;
  requirements_refs?: string[];
  children?: FeatureNode[];
};

type FeatureTreePayload = {
  module_catalog?: { modules?: Array<{ module_id: string; name?: string }> };
  feature_tree?: FeatureNode[];
  new_modules?: Array<{ proposed_id?: string; name?: string; justification?: string }>;
  modularization_report?: {
    reuse_count?: number;
    new_module_count?: number;
    violations?: Array<{ feature_id?: string; issue?: string }>;
  };
  mermaid?: string;
  raw_feature_tree?: string;
};

const NO_DATA_MERMAID = 'graph TD\n  A[Feature Tree] --> B[No data]';
const sanitizeNodeId = (value: string) => value.replace(/[^a-zA-Z0-9_]/g, '_');

function tryParseJson<T = unknown>(text: string): T | undefined {
  try {
    return JSON.parse(text) as T;
  } catch {
    return undefined;
  }
}

function extractJsonPayload(text: string): unknown | undefined {
  const trimmed = text.trim();
  if (!trimmed) return undefined;

  const direct = tryParseJson(trimmed);
  if (direct !== undefined) return direct;

  const fenced = trimmed.match(/```(?:json)?\s*([\s\S]*?)```/i);
  if (fenced?.[1]) {
    const fencedParsed = tryParseJson(fenced[1].trim());
    if (fencedParsed !== undefined) return fencedParsed;
  }

  const candidates: string[] = [];
  const firstBrace = trimmed.indexOf('{');
  const lastBrace = trimmed.lastIndexOf('}');
  if (firstBrace !== -1 && lastBrace > firstBrace) {
    candidates.push(trimmed.slice(firstBrace, lastBrace + 1));
  }
  const firstBracket = trimmed.indexOf('[');
  const lastBracket = trimmed.lastIndexOf(']');
  if (firstBracket !== -1 && lastBracket > firstBracket) {
    candidates.push(trimmed.slice(firstBracket, lastBracket + 1));
  }

  for (const candidate of candidates) {
    const parsed = tryParseJson(candidate);
    if (parsed !== undefined) return parsed;
  }

  return undefined;
}

function normalizeFeatureTreePayload(parsed: unknown): FeatureTreePayload | undefined {
  if (Array.isArray(parsed)) {
    return { feature_tree: parsed as FeatureNode[] };
  }
  if (!parsed || typeof parsed !== 'object') return undefined;

  const payload: FeatureTreePayload = { ...(parsed as FeatureTreePayload) };

  const coerceTree = (value: unknown): FeatureNode[] | undefined => {
    if (Array.isArray(value)) return value as FeatureNode[];
    if (typeof value === 'string') {
      const parsedValue = extractJsonPayload(value);
      const normalized = normalizeFeatureTreePayload(parsedValue);
      return normalized?.feature_tree;
    }
    if (value && typeof value === 'object') {
      const maybeTree = (value as FeatureTreePayload).feature_tree;
      if (Array.isArray(maybeTree)) return maybeTree;
    }
    return undefined;
  };

  const featureTree = coerceTree(payload.feature_tree);
  if (featureTree) {
    payload.feature_tree = featureTree;
  }

  if ((!payload.feature_tree || payload.feature_tree.length === 0) && typeof payload.raw_feature_tree === 'string') {
    const recovered = extractJsonPayload(payload.raw_feature_tree);
    const normalized = normalizeFeatureTreePayload(recovered);
    if (normalized?.feature_tree) {
      payload.feature_tree = normalized.feature_tree;
    }
    if (!payload.module_catalog && normalized?.module_catalog) {
      payload.module_catalog = normalized.module_catalog;
    }
    if (!payload.new_modules && normalized?.new_modules) {
      payload.new_modules = normalized.new_modules;
    }
    if (!payload.modularization_report && normalized?.modularization_report) {
      payload.modularization_report = normalized.modularization_report;
    }
    if (!payload.mermaid && normalized?.mermaid) {
      payload.mermaid = normalized.mermaid;
    }
  }

  return payload;
}

function buildMermaidFromTree(featureTree: FeatureNode[], collapsedNodes: Set<string>): string {
  if (!featureTree || featureTree.length === 0) {
    return NO_DATA_MERMAID;
  }

  const lines: string[] = [
    'graph TD',
    'classDef root fill:#f3f4f6,stroke:#9ca3af,color:#111827;',
    'classDef reuseExisting fill:#dcfce7,stroke:#16a34a,color:#166534;',
    'classDef extendExisting fill:#dbeafe,stroke:#2563eb,color:#1e3a8a;',
    'classDef newModule fill:#fef3c7,stroke:#d97706,color:#92400e;',
    'classDef defaultNode fill:#e5e7eb,stroke:#9ca3af,color:#111827;',
  ];
  const rootId = 'PlatformRoot';
  lines.push(`${rootId}["Platform Feature Tree"]:::root`);
  const seen = new Set<string>();

  const getClassName = (node: FeatureNode) => {
    switch (node.reuse_decision) {
      case 'reuse_existing':
        return 'reuseExisting';
      case 'extend_existing':
        return 'extendExisting';
      case 'new_module':
        return 'newModule';
      default:
        return 'defaultNode';
    }
  };

  const addNode = (node: FeatureNode, parentId: string) => {
    const rawId = node.id || node.name || 'feature';
    const nodeId = sanitizeNodeId(rawId);
    let label = (node.name || rawId).replace(/"/g, "'");
    if (node.module_id) {
      const moduleLabel = String(node.module_id).replace(/"/g, "'");
      label = `${label}<br/>[${moduleLabel}]`;
    }

    const hasChildren = (node.children || []).length > 0;
    const isCollapsed = collapsedNodes.has(nodeId);
    if (hasChildren) {
      label = `${isCollapsed ? '[+]' : '[-]'} ${label}`;
    }

    label = label.replace(/\n/g, '<br/>');

    if (!seen.has(nodeId)) {
      lines.push(`${nodeId}["${label}"]:::${getClassName(node)}`);
      seen.add(nodeId);
    }
    lines.push(`${parentId} --> ${nodeId}`);

    if (!isCollapsed) {
      (node.children || []).forEach((child) => addNode(child, nodeId));
    }
  };

  featureTree.forEach((node) => addNode(node, rootId));
  return lines.join('\n');
}

export function FeatureTree() {
  const { jobId } = useParams<{ jobId: string }>();
  const location = useLocation();
  const { data: job } = useJob(jobId);
  const { data: artifactsData, isLoading } = useArtifacts(jobId);
  const [isGraphFullscreen, setIsGraphFullscreen] = useState(false);
  const [viewMode, setViewMode] = useState<'visual' | 'pdf'>('visual');
  const [collapsedNodes, setCollapsedNodes] = useState<Set<string>>(new Set());

  const artifacts = artifactsData?.artifacts || [];
  const featureTreeArtifact = artifacts.find(a => a.artifact_type === 'feature_tree');
  const returnPath = (location.state as { from?: string } | null)?.from;
  const backLink = returnPath
    ? { href: returnPath, label: 'Back' }
    : { href: `/project/${jobId}`, label: 'Back to Project' };
  const currentPath = `${location.pathname}${location.search}`;

  const parsed = useMemo(() => parseFeatureTree(featureTreeArtifact), [featureTreeArtifact]);
  const payload = parsed.payload;

  const featureTree = payload?.feature_tree || [];
  const moduleCount = payload?.module_catalog?.modules?.length || 0;
  const reuseCount = payload?.modularization_report?.reuse_count ?? 0;
  const newModuleCount = payload?.modularization_report?.new_module_count ?? 0;
  const violations = payload?.modularization_report?.violations || [];
  const newModules = payload?.new_modules || [];

  useEffect(() => {
    setCollapsedNodes(new Set());
  }, [featureTreeArtifact?.artifact_id]);

  const nodeIndex = useMemo(() => {
    const map = new Map<string, string>();
    const walk = (nodes: FeatureNode[]) => {
      nodes.forEach((node) => {
        const rawId = node.id || node.name || 'feature';
        const nodeId = sanitizeNodeId(rawId);
        map.set(nodeId, nodeId);
        if (node.id) map.set(node.id, nodeId);
        if (node.name) map.set(node.name, nodeId);
        const children = node.children || [];
        if (children.length > 0) walk(children);
      });
    };
    if (featureTree.length > 0) walk(featureTree);
    return map;
  }, [featureTree]);

  const collapsibleNodes = useMemo(() => {
    const set = new Set<string>();
    const walk = (nodes: FeatureNode[]) => {
      nodes.forEach((node) => {
        const nodeId = sanitizeNodeId(node.id || node.name || 'feature');
        const children = node.children || [];
        if (children.length > 0) {
          set.add(nodeId);
          walk(children);
        }
      });
    };
    if (featureTree.length > 0) walk(featureTree);
    return set;
  }, [featureTree]);

  const normalizeMermaidId = useCallback((rawId: string) => {
    const trimmed = rawId.replace(/^flowchart-/, '').replace(/-\d+$/, '');
    return sanitizeNodeId(trimmed);
  }, []);

  const handleNodeClick = useCallback((rawId: string) => {
    const normalizeLabel = (value: string) => {
      const cleaned = value.replace(/<br\s*\/?>/gi, '\n');
      const firstLine = cleaned.split('\n')[0] || cleaned;
      const withoutPrefix = firstLine.replace(/^\[\+\]\s*|^\[\-\]\s*/g, '');
      return withoutPrefix.replace(/\s*\[[^\]]+\]\s*$/, '').trim();
    };

    const candidate = nodeIndex.get(rawId)
      || nodeIndex.get(normalizeMermaidId(rawId))
      || nodeIndex.get(sanitizeNodeId(rawId))
      || nodeIndex.get(normalizeLabel(rawId))
      || nodeIndex.get(sanitizeNodeId(normalizeLabel(rawId)))
      || normalizeMermaidId(rawId);

    if (!candidate || !collapsibleNodes.has(candidate)) return;
    setCollapsedNodes((prev) => {
      const next = new Set(prev);
      if (next.has(candidate)) {
        next.delete(candidate);
      } else {
        next.add(candidate);
      }
      return next;
    });
  }, [collapsibleNodes, nodeIndex, normalizeMermaidId]);

  const mermaid = useMemo(() => {
    const candidate = (payload?.mermaid || '').trim();
    const normalized = candidate.replace(/\s+/g, ' ').trim();
    const isNoData = normalized === NO_DATA_MERMAID.replace(/\s+/g, ' ').trim()
      || (featureTree.length > 0 && normalized.includes('No data'));

    if (featureTree.length > 0) {
      return buildMermaidFromTree(featureTree, collapsedNodes);
    }
    if (!candidate || isNoData) {
      return NO_DATA_MERMAID;
    }
    return candidate;
  }, [collapsedNodes, featureTree, payload?.mermaid]);

  useEffect(() => {
    if (!isGraphFullscreen) return;
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setIsGraphFullscreen(false);
    };
    document.addEventListener('keydown', handleEscape);
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = 'unset';
    };
  }, [isGraphFullscreen]);

  return (
    <PageLayout>
      <PageHeader
        title="Feature Tree"
        description={
          <div className="flex items-center gap-2 mt-1">
            <span className="text-text-secondary">{job?.project_id}</span>
            {featureTreeArtifact?.created_at && (
              <Badge variant="info" size="sm">
                Updated {formatRelativeTime(featureTreeArtifact.created_at)}
              </Badge>
            )}
          </div>
        }
        backLink={backLink}
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant={viewMode === 'visual' ? 'primary' : 'ghost'}
              size="sm"
              onClick={() => setViewMode('visual')}
            >
              Visual
            </Button>
            <Button
              variant={viewMode === 'pdf' ? 'primary' : 'ghost'}
              size="sm"
              onClick={() => setViewMode('pdf')}
              disabled={!featureTreeArtifact?.artifact_id}
            >
              PDF Preview
            </Button>
            <Link to={`/project/${jobId}/deliverables`} state={{ from: currentPath }}>
              <Button variant="outline">All Deliverables</Button>
            </Link>
          </div>
        }
      />

      {isLoading && (
        <Card className="text-center py-12">
          <div className="text-text-secondary">Loading feature tree...</div>
        </Card>
      )}

      {!isLoading && !featureTreeArtifact && (
        <Card className="text-center py-12">
          <AlertCircle className="w-12 h-12 text-text-muted mx-auto mb-4" />
          <p className="text-text-secondary mb-2">No feature tree available yet</p>
          <p className="text-sm text-text-secondary mb-4">
            The feature tree is generated after PRD approval.
          </p>
          <Link to={`/project/${jobId}`}>
            <Button variant="outline">View Pipeline Status</Button>
          </Link>
        </Card>
      )}

      {!isLoading && featureTreeArtifact && viewMode === 'visual' && (
        <div className="space-y-6">
          {/* Summary Metrics */}
          <div className="grid md:grid-cols-3 gap-4">
            <SummaryCard
              icon={<Layers className="w-5 h-5 text-primary-600" />}
              label="Module Catalog"
              value={`${moduleCount} modules`}
              detail="Available platform modules"
            />
            <SummaryCard
              icon={<GitBranch className="w-5 h-5 text-success-600" />}
              label="Reuse Count"
              value={`${reuseCount}`}
              detail="Features mapped to existing modules"
            />
            <SummaryCard
              icon={<Box className="w-5 h-5 text-warning-600" />}
              label="New Modules"
              value={`${newModuleCount}`}
              detail="Proposed platform expansions"
            />
          </div>

          {/* Feature Tree */}
          <Card>
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-text-primary">Modular Feature Tree</h3>
              <Badge variant="info">{featureTree.length} roots</Badge>
            </div>
            {featureTree.length === 0 ? (
              <p className="text-sm text-text-secondary">No structured tree found.</p>
            ) : (
              <div className="space-y-4">
                {featureTree.map((node, idx) => (
                  <FeatureNodeView key={`${node.id || node.name}-${idx}`} node={node} depth={0} />
                ))}
              </div>
            )}
          </Card>

          {/* Mermaid Diagram */}
          <Card>
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-text-primary">Feature Tree Diagram</h3>
              <Badge variant="info">Mermaid</Badge>
            </div>
            <MermaidDiagram
              chart={mermaid}
              onToggleFullscreen={() => setIsGraphFullscreen(true)}
              containerClassName="h-[420px]"
              onNodeClick={handleNodeClick}
              fitKey={featureTreeArtifact?.artifact_id || 'feature-tree-inline'}
            />
          </Card>

          {/* Modularization Report */}
          <Card>
            <h3 className="font-semibold text-text-primary mb-4">Modularization Report</h3>
            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <h4 className="text-sm font-semibold text-text-secondary mb-2">New Modules</h4>
                {newModules.length === 0 && (
                  <p className="text-sm text-text-secondary">No new modules proposed.</p>
                )}
                {newModules.length > 0 && (
                  <ul className="space-y-2">
                    {newModules.map((mod, idx) => (
                      <li key={`${mod.proposed_id || mod.name}-${idx}`} className="text-sm">
                        <div className="font-medium text-text-primary">
                          {mod.proposed_id || mod.name || 'New module'}
                        </div>
                        {mod.justification && (
                          <div className="text-text-secondary">{mod.justification}</div>
                        )}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
              <div>
                <h4 className="text-sm font-semibold text-text-secondary mb-2">Violations</h4>
                {violations.length === 0 && (
                  <p className="text-sm text-text-secondary">No modularization violations.</p>
                )}
                {violations.length > 0 && (
                  <ul className="space-y-2">
                    {violations.map((violation, idx) => (
                      <li key={`${violation.feature_id || 'violation'}-${idx}`} className="text-sm">
                        <div className="font-medium text-text-primary">
                          {violation.feature_id || 'Feature'}
                        </div>
                        <div className="text-text-secondary">{violation.issue}</div>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          </Card>

          {parsed.error && (
            <Card variant="outlined" className="border-warning-200 bg-warning-50">
              <div className="text-warning-700 text-sm">
                Could not parse feature tree JSON. Showing raw content below.
              </div>
              <pre className="mt-3 text-xs text-text-secondary whitespace-pre-wrap">
                {featureTreeArtifact?.content}
              </pre>
            </Card>
          )}
        </div>
      )}

      {!isLoading && featureTreeArtifact && viewMode === 'pdf' && (
        <Card>
          <PdfPreview artifactId={featureTreeArtifact.artifact_id} />
        </Card>
      )}
      {isGraphFullscreen && (
        <div className="fixed inset-0 z-50 bg-black/70">
          <div className="absolute inset-0 bg-bg-primary">
            <div className="h-full w-full p-6 flex flex-col gap-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-semibold text-text-primary">Feature Tree Diagram</h3>
                  <p className="text-sm text-text-secondary">Drag to pan, scroll to zoom.</p>
                </div>
                <Button variant="outline" onClick={() => setIsGraphFullscreen(false)}>
                  Close
                </Button>
              </div>
              <div className="flex-1">
                <MermaidDiagram
                  chart={mermaid}
                  isFullscreen
                  onToggleFullscreen={() => setIsGraphFullscreen(false)}
                  containerClassName="h-[calc(100vh-220px)]"
                  onNodeClick={handleNodeClick}
                  fitKey={`${featureTreeArtifact?.artifact_id || 'feature-tree-full'}:fullscreen`}
                />
              </div>
            </div>
          </div>
        </div>
      )}
    </PageLayout>
  );
}

function SummaryCard({
  icon,
  label,
  value,
  detail,
}: {
  icon: ReactNode;
  label: string;
  value: string;
  detail: string;
}) {
  return (
    <Card variant="outlined">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-full bg-bg-tertiary flex items-center justify-center">
          {icon}
        </div>
        <div>
          <p className="text-xs text-text-secondary uppercase tracking-wide">{label}</p>
          <p className="text-lg font-semibold text-text-primary">{value}</p>
          <p className="text-xs text-text-secondary">{detail}</p>
        </div>
      </div>
    </Card>
  );
}

function FeatureNodeView({ node, depth }: { node: FeatureNode; depth: number }) {
  const children = node.children || [];
  const label = node.name || node.id || 'Feature';
  const moduleId = node.module_id;
  const reuse = node.reuse_decision;

  return (
    <div className="space-y-2">
      <div className="flex items-start gap-3">
        <div
          className="w-2 h-2 rounded-full bg-primary-500 mt-2"
          style={{ marginLeft: `${depth * 16}px` }}
        />
        <div className="flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-medium text-text-primary">{label}</span>
            {moduleId && (
              <Badge variant="info" size="sm">
                {moduleId}
              </Badge>
            )}
            {reuse && (
              <Badge variant={reuse === 'new_module' ? 'warning' : 'success'} size="sm">
                {reuse.replace(/_/g, ' ')}
              </Badge>
            )}
          </div>
          {node.description && (
            <p className="text-sm text-text-secondary mt-1">{node.description}</p>
          )}
          {node.requirements_refs && node.requirements_refs.length > 0 && (
            <p className="text-xs text-text-muted mt-1">
              {node.requirements_refs.join(', ')}
            </p>
          )}
        </div>
      </div>
      {children.length > 0 && (
        <div className="space-y-3">
          {children.map((child, idx) => (
            <FeatureNodeView key={`${child.id || child.name}-${idx}`} node={child} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  );
}

function parseFeatureTree(artifact?: Artifact): { payload?: FeatureTreePayload; error?: string } {
  if (!artifact?.content) return {};
  try {
    const parsed = extractJsonPayload(artifact.content);
    if (parsed === undefined) {
      return { error: 'Invalid JSON' };
    }
    const payload = normalizeFeatureTreePayload(parsed);
    if (!payload) {
      return { error: 'Invalid JSON' };
    }
    return { payload };
  } catch (err) {
    return { error: err instanceof Error ? err.message : 'Invalid JSON' };
  }
}
