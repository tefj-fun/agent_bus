import { cn } from '../../utils/utils';
import { Check, X, Loader2 } from 'lucide-react';
import type { WorkflowStage, StageInfo } from '../../types';
import { WORKFLOW_STAGES, getStageIndex } from '../../types';

interface WorkflowProgressProps {
  currentStage: WorkflowStage;
  failedStage?: WorkflowStage;
  orientation?: 'horizontal' | 'vertical';
  compact?: boolean;
  currentStageOverride?: 'completed' | 'active';
}

export function WorkflowProgress({
  currentStage,
  failedStage,
  orientation = 'horizontal',
  compact = false,
  currentStageOverride,
}: WorkflowProgressProps) {
  const isTerminalCompleted = currentStage === 'completed';
  const currentIndex = getStageIndex(currentStage);
  const failedIndex = failedStage ? getStageIndex(failedStage) : -1;

  const baseStages = WORKFLOW_STAGES.filter(stage => {
    if (stage.id === 'failed') return currentStage === 'failed' || failedStage === 'failed';
    if (stage.id === 'completed') return currentStage === 'completed';
    return true;
  });
  const uniqueStages = Array.from(new Map(baseStages.map(stage => [stage.id, stage])).values());

  // For display, we show a simplified set of stages
  const displayStages = compact
    ? uniqueStages.filter((_, i) => i % 2 === 0 || i === uniqueStages.length - 1)
    : uniqueStages;

  const getStageStatus = (stage: StageInfo, _index: number): 'completed' | 'active' | 'failed' | 'pending' => {
    const stageIndex = getStageIndex(stage.id);
    if (isTerminalCompleted) return 'completed';
    if (failedIndex >= 0 && stageIndex === failedIndex) return 'failed';
    if (stageIndex < currentIndex) return 'completed';
    if (stageIndex === currentIndex) return currentStageOverride || 'active';
    return 'pending';
  };

  if (orientation === 'vertical') {
    return (
      <div className="space-y-4">
        {displayStages.map((stage, i) => {
          const status = getStageStatus(stage, i);
          return (
            <div key={stage.id} className="flex items-start gap-3">
              <StageIcon status={status} icon={stage.icon} />
              <div className="flex-1 min-w-0 pt-0.5">
                <p className={cn(
                  'font-medium',
                  status === 'completed' && 'text-text-secondary',
                  status === 'active' && 'text-primary-600',
                  status === 'failed' && 'text-error-600',
                  status === 'pending' && 'text-text-muted'
                )}>
                  {stage.name}
                </p>
                {status === 'active' && (
                  <p className="text-sm text-text-secondary mt-0.5">In progress...</p>
                )}
              </div>
            </div>
          );
        })}
      </div>
    );
  }

  return (
    <div className="w-full overflow-x-auto">
      <div className="flex items-start justify-between flex-nowrap min-w-max">
        {displayStages.map((stage, i) => {
          const status = getStageStatus(stage, i);
          const isLast = i === displayStages.length - 1;

          return (
            <div key={stage.id} className="flex items-start flex-1 basis-0 min-w-[3.5rem]">
              <div className="flex flex-col items-center w-full">
                <StageIcon status={status} icon={stage.icon} />
                <div className={cn(
                  'text-[10px] mt-1 font-medium text-center leading-[1.1] min-h-[1.5rem]',
                  status === 'completed' && 'text-text-secondary',
                  status === 'active' && 'text-primary-600',
                  status === 'failed' && 'text-error-600',
                  status === 'pending' && 'text-text-muted'
                )}>
                  {stage.name}
                </div>
              </div>
              {!isLast && (
                <div className={cn(
                  'flex-1 h-0.5 mx-0.5 mt-2.5',
                  status === 'completed' ? 'bg-success-500' : 'bg-border'
                )} />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function StageIcon({ status, icon }: { status: 'completed' | 'active' | 'failed' | 'pending'; icon: string }) {
  const baseClasses = 'w-8 h-8 rounded-full flex items-center justify-center text-sm';

  if (status === 'completed') {
    return (
      <div className={cn(baseClasses, 'bg-success-100 text-success-600')}>
        <Check className="w-4 h-4" />
      </div>
    );
  }

  if (status === 'active') {
    return (
      <div className={cn(baseClasses, 'bg-primary-100 text-primary-600 animate-pulse')}>
        <Loader2 className="w-4 h-4 animate-spin" />
      </div>
    );
  }

  if (status === 'failed') {
    return (
      <div className={cn(baseClasses, 'bg-error-100 text-error-600')}>
        <X className="w-4 h-4" />
      </div>
    );
  }

  const normalizedIcon = icon.replace(/[\uFE0E\uFE0F]/g, '').trim() || '?';

  return (
    <div className={cn(baseClasses, 'bg-bg-tertiary text-text-muted')}>
      <span className="inline-flex items-center justify-center leading-none text-[11px] font-semibold">
        {normalizedIcon}
      </span>
    </div>
  );
}
