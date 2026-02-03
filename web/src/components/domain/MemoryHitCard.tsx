import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { Button } from '../ui/Button';
import { Eye, Sparkles } from 'lucide-react';
import { truncate } from '../../utils/utils';

interface MemoryHitCardProps {
  id: string;
  title: string;
  patternType: string;
  similarity: number;
  preview: string;
  usageCount?: number;
  successRate?: number;
  projectId?: string;
  onViewDetails?: () => void;
  onUseTemplate?: () => void;
}

export function MemoryHitCard({
  id: _id,
  title,
  patternType,
  similarity,
  preview,
  usageCount,
  successRate,
  projectId,
  onViewDetails,
  onUseTemplate,
}: MemoryHitCardProps) {
  const similarityPercent = Math.round(similarity * 100);

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'prd':
        return 'purple';
      case 'architecture':
        return 'warning';
      case 'plan':
        return 'info';
      default:
        return 'default';
    }
  };

  return (
    <Card variant="outlined" padding="md" className="hover:border-primary-300 transition-colors">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h4 className="font-medium text-gray-900 truncate">{title}</h4>
            <Badge variant={getTypeColor(patternType)} size="sm">
              {patternType}
            </Badge>
          </div>

          <p className="text-sm text-gray-600 line-clamp-2 mb-2">
            {truncate(preview, 150)}
          </p>

          <div className="flex items-center gap-3 text-xs text-gray-500">
            <span className="font-medium text-primary-600">
              {similarityPercent}% match
            </span>
            {usageCount !== undefined && (
              <span>Used {usageCount} times</span>
            )}
            {successRate !== undefined && (
              <span className="text-success-600">
                {Math.round(successRate * 100)}% success
              </span>
            )}
            {projectId && (
              <span className="truncate">from: {projectId}</span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span
            className={`text-lg font-bold ${
              similarityPercent >= 90
                ? 'text-success-600'
                : similarityPercent >= 70
                ? 'text-primary-600'
                : 'text-gray-500'
            }`}
          >
            {similarityPercent}%
          </span>
        </div>
      </div>

      <div className="flex items-center gap-2 mt-3 pt-3 border-t border-gray-100">
        {onViewDetails && (
          <Button
            variant="ghost"
            size="sm"
            icon={<Eye className="w-4 h-4" />}
            onClick={onViewDetails}
          >
            View
          </Button>
        )}
        {onUseTemplate && (
          <Button
            variant="outline"
            size="sm"
            icon={<Sparkles className="w-4 h-4" />}
            onClick={onUseTemplate}
          >
            Use Pattern
          </Button>
        )}
      </div>
    </Card>
  );
}

// Simplified version for sidebar
export function MemoryHitBadge({
  title,
  similarity,
  onClick,
}: {
  title: string;
  similarity: number;
  onClick?: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="flex items-center justify-between w-full px-3 py-2 text-sm rounded-lg hover:bg-gray-50 transition-colors"
    >
      <span className="truncate text-gray-700">{title}</span>
      <span className="text-xs font-medium text-primary-600 ml-2">
        {Math.round(similarity * 100)}%
      </span>
    </button>
  );
}
