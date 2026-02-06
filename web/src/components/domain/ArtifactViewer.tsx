import { useEffect, useState } from 'react';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';
import { Copy, Download, Check, ChevronDown, ChevronUp } from 'lucide-react';
import { cn } from '../../utils/utils';
import { ArtifactContent, supportsA4View } from './ArtifactContent';
import { PdfPreview } from './PdfPreview';
import type { ArtifactType } from '../../types';

interface ArtifactViewerProps {
  artifactId?: string;
  type: ArtifactType;
  content: string;
  title?: string;
  createdAt?: string;
  collapsible?: boolean;
  defaultExpanded?: boolean;
  actions?: React.ReactNode;
}

export function ArtifactViewer({
  artifactId,
  type,
  content,
  title,
  createdAt,
  collapsible = false,
  defaultExpanded = true,
  actions,
}: ArtifactViewerProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const [copied, setCopied] = useState(false);
  const [a4View, setA4View] = useState(supportsA4View(type));
  const [viewMode, setViewMode] = useState<'markdown' | 'pdf'>('markdown');
  const showA4Toggle = supportsA4View(type);

  useEffect(() => {
    setA4View(supportsA4View(type));
    setViewMode('markdown');
  }, [type]);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const blob = new Blob([content], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${type}-${Date.now()}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const getTypeInfo = (t: ArtifactType) => {
    const types: Record<ArtifactType, { label: string; icon: string; color: 'purple' | 'warning' | 'info' | 'success' | 'error' | 'default' }> = {
      prd: { label: 'PRD', icon: '📄', color: 'purple' },
      feature_tree: { label: 'Feature Tree', icon: '🌳', color: 'info' },
      feature_tree_graph: { label: 'Feature Tree Graph', icon: '📈', color: 'info' },
      plan: { label: 'Plan', icon: '📋', color: 'info' },
      project_plan: { label: 'Project Plan', icon: '🗺️', color: 'info' },
      architecture: { label: 'Architecture', icon: '🏗️', color: 'warning' },
      uiux: { label: 'UI/UX', icon: '🎨', color: 'info' },
      development: { label: 'Development', icon: '💻', color: 'info' },
      qa: { label: 'QA', icon: '🧪', color: 'success' },
      security: { label: 'Security', icon: '🔒', color: 'error' },
      documentation: { label: 'Documentation', icon: '📚', color: 'default' },
      support: { label: 'Support', icon: '🎧', color: 'default' },
      pm_review: { label: 'PM Review', icon: '🧑‍💼', color: 'warning' },
      delivery: { label: 'Delivery', icon: '📦', color: 'success' },
    };

    return types[t] || { label: t, icon: '📄', color: 'default' as const };
  };

  const typeInfo = getTypeInfo(type);

  return (
    <Card variant="outlined" padding="none">
      {/* Header */}
      <div
        className={cn(
          'flex items-center justify-between px-4 py-3 border-b border-border',
          collapsible && 'cursor-pointer hover:bg-bg-secondary'
        )}
        onClick={collapsible ? () => setExpanded(!expanded) : undefined}
      >
        <div className="flex items-center gap-3">
          <span className="text-lg">{typeInfo.icon}</span>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-medium text-text-primary">
                {title || typeInfo.label}
              </h3>
              <Badge variant={typeInfo.color} size="sm">
                {typeInfo.label}
              </Badge>
            </div>
            {createdAt && (
              <p className="text-xs text-text-secondary">
                Generated {new Date(createdAt).toLocaleString()}
              </p>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          {!collapsible && (
            <>
              <Button
                variant={viewMode === 'markdown' ? 'primary' : 'ghost'}
                size="sm"
                onClick={(e) => {
                  e.stopPropagation();
                  setViewMode('markdown');
                }}
              >
                Markdown
              </Button>
              <Button
                variant={viewMode === 'pdf' ? 'primary' : 'ghost'}
                size="sm"
                onClick={(e) => {
                  e.stopPropagation();
                  if (artifactId) setViewMode('pdf');
                }}
                disabled={!artifactId}
              >
                PDF Preview
              </Button>
              {showA4Toggle && (
                <Button
                  variant={a4View ? 'primary' : 'ghost'}
                  size="sm"
                  onClick={(e) => {
                    e.stopPropagation();
                    setA4View((prev) => !prev);
                  }}
                  disabled={viewMode === 'pdf'}
                >
                  {a4View ? 'A4 View On' : 'A4 View Off'}
                </Button>
              )}
              <Button
                variant="ghost"
                size="sm"
                icon={copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                onClick={(e) => {
                  e.stopPropagation();
                  handleCopy();
                }}
              >
                {copied ? 'Copied' : 'Copy'}
              </Button>
              <Button
                variant="ghost"
                size="sm"
                icon={<Download className="w-4 h-4" />}
                onClick={(e) => {
                  e.stopPropagation();
                  handleDownload();
                }}
              >
                Download
              </Button>
            </>
          )}
          {collapsible && (
            expanded ? (
              <ChevronUp className="w-5 h-5 text-text-muted" />
            ) : (
              <ChevronDown className="w-5 h-5 text-text-muted" />
            )
          )}
        </div>
      </div>

      {/* Content */}
      {expanded && (
        <div className="p-4">
          {viewMode === 'pdf' ? (
            <PdfPreview artifactId={artifactId} />
          ) : (
            <ArtifactContent type={type} content={content} a4View={a4View} />
          )}
          {actions && (
            <div className="mt-4 pt-4 border-t border-border">
              {actions}
            </div>
          )}
        </div>
      )}
    </Card>
  );
}

// Compact card for deliverables list
export function ArtifactCard({
  type,
  title,
  size,
  createdAt,
  onView,
  onDownload,
}: {
  type: ArtifactType;
  title?: string;
  size?: number;
  createdAt?: string;
  onView?: () => void;
  onDownload?: () => void;
}) {
  const getTypeInfo = (t: ArtifactType) => {
    const types: Record<ArtifactType, { label: string; icon: string }> = {
      prd: { label: 'Product Requirements Document', icon: '📄' },
      feature_tree: { label: 'Feature Tree', icon: '🌳' },
      feature_tree_graph: { label: 'Feature Tree Graph', icon: '📈' },
      plan: { label: 'Project Plan', icon: '📋' },
      project_plan: { label: 'Project Plan', icon: '🗺️' },
      architecture: { label: 'System Architecture', icon: '🏗️' },
      uiux: { label: 'UI/UX Design System', icon: '🎨' },
      development: { label: 'Development Plan', icon: '💻' },
      qa: { label: 'QA Test Plan', icon: '🧪' },
      security: { label: 'Security Review', icon: '🔒' },
      documentation: { label: 'Technical Documentation', icon: '📚' },
      support: { label: 'Support Documentation', icon: '🎧' },
      pm_review: { label: 'Product Manager Review', icon: '🧑‍💼' },
      delivery: { label: 'Delivery Package', icon: '📦' },
    };

    return types[t] || { label: t, icon: '📄' };
  };

  const typeInfo = getTypeInfo(type);

  const formatSize = (bytes?: number) => {
    if (!bytes) return '';
    if (bytes < 1024) return `${bytes} B`;
    return `${(bytes / 1024).toFixed(1)} KB`;
  };

  return (
    <Card variant="outlined" padding="md" className="hover:border-primary-300 transition-colors">
      <div className="flex items-start gap-3">
        <span className="text-2xl">{typeInfo.icon}</span>
        <div className="flex-1 min-w-0">
          <h4 className="font-medium text-text-primary">
            {title || typeInfo.label}
          </h4>
          <div className="flex items-center gap-2 text-xs text-text-secondary mt-1">
            {createdAt && (
              <span>Generated {new Date(createdAt).toLocaleDateString()}</span>
            )}
            {size && (
              <>
                <span>·</span>
                <span>{formatSize(size)}</span>
              </>
            )}
          </div>
        </div>
      </div>
      <div className="flex items-center gap-2 mt-3">
        {onView && (
          <Button variant="outline" size="sm" onClick={onView}>
            View
          </Button>
        )}
        {onDownload && (
          <Button
            variant="ghost"
            size="sm"
            icon={<Download className="w-4 h-4" />}
            onClick={onDownload}
          >
            Download
          </Button>
        )}
      </div>
    </Card>
  );
}
