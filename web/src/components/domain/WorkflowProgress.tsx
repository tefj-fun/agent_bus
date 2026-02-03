import { cn } from '../../utils/utils';
import { Check, X, Loader2 } from 'lucide-react';
import type { WorkflowStage, StageInfo } from '../../types';
import { WORKFLOW_STAGES, getStageIndex } from '../../types';

interface WorkflowProgressProps {
  currentStage: WorkflowStage;
  failedStage?: WorkflowStage;
  orientation?: 'horizontal' | 'vertical';
  compact?: boolean;
}

export function WorkflowProgress({
  currentStage,
  failedStage,
  orientation = 'horizontal',
  compact = false,
}: WorkflowProgressProps) {
  const currentIndex = getStageIndex(currentStage);
  const failedIndex = failedStage ? getStageIndex(failedStage) : -1;

  // For display, we show a simplified set of stages
  const displayStages = compact
    ? WORKFLOW_STAGES.filter((_, i) => i % 2 === 0 || i === WORKFLOW_STAGES.length - 1)
    : WORKFLOW_STAGES;

  const getStageStatus = (stage: StageInfo, _index: number): 'completed' | 'active' | 'failed' | 'pending' => {
    const stageIndex = getStageIndex(stage.id);
    if (failedIndex >= 0 && stageIndex === failedIndex) return 'failed';
    if (stageIndex < currentIndex) return 'completed';
    if (stageIndex === currentIndex) return 'active';
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
                  status === 'completed' && 'text-gray-600',
                  status === 'active' && 'text-primary-600',
                  status === 'failed' && 'text-error-600',
                  status === 'pending' && 'text-gray-400'
                )}>
                  {stage.name}
                </p>
                {status === 'active' && (
                  <p className="text-sm text-gray-500 mt-0.5">In progress...</p>
                )}
              </div>
            </div>
          );
        })}
      </div>
    );
  }

  return (
    <div className="w-full">
      <div className="flex items-center justify-between">
        {displayStages.map((stage, i) => {
          const status = getStageStatus(stage, i);
          const isLast = i === displayStages.length - 1;

          return (
            <div key={stage.id} className="flex items-center flex-1">
              <div className="flex flex-col items-center">
                <StageIcon status={status} icon={stage.icon} />
                <span className={cn(
                  'text-xs mt-1.5 font-medium text-center',
                  status === 'completed' && 'text-gray-600',
                  status === 'active' && 'text-primary-600',
                  status === 'failed' && 'text-error-600',
                  status === 'pending' && 'text-gray-400'
                )}>
                  {stage.name}
                </span>
              </div>
              {!isLast && (
                <div className={cn(
                  'flex-1 h-0.5 mx-2 mt-[-1rem]',
                  status === 'completed' ? 'bg-success-500' : 'bg-gray-200'
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

  return (
    <div className={cn(baseClasses, 'bg-gray-100 text-gray-400')}>
      <span>{icon}</span>
    </div>
  );
}
