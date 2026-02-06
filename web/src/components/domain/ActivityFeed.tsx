import { useEffect, useState } from 'react';
import { formatRelativeTime } from '../../utils/utils';
import { cn } from '../../utils/utils';
import type { AgentEvent, EventType } from '../../types';
import {
  Rocket,
  PlayCircle,
  CheckCircle,
  AlertCircle,
  Clock,
  ThumbsUp,
  ThumbsDown,
  XCircle,
} from 'lucide-react';

interface ActivityFeedProps {
  events: AgentEvent[];
  maxItems?: number;
  showTimestamps?: boolean;
}

export function ActivityFeed({
  events,
  maxItems = 20,
  showTimestamps = true,
}: ActivityFeedProps) {
  const [, setTick] = useState(0);

  useEffect(() => {
    if (!showTimestamps) return;
    const interval = setInterval(() => {
      setTick((tick) => tick + 1);
    }, 30000);
    return () => clearInterval(interval);
  }, [showTimestamps]);

  const displayEvents = events.slice(0, maxItems);

  if (displayEvents.length === 0) {
    return (
      <div className="text-center py-8 text-text-secondary">
        <Clock className="w-8 h-8 mx-auto mb-2 opacity-50" />
        <p className="text-sm">No activity yet</p>
      </div>
    );
  }

  return (
    <div className="space-y-1">
      {displayEvents.map((event) => (
        <ActivityItem
          key={event.id}
          event={event}
          showTimestamp={showTimestamps}
        />
      ))}
    </div>
  );
}

function ActivityItem({
  event,
  showTimestamp,
}: {
  event: AgentEvent;
  showTimestamp: boolean;
}) {
  const { icon: Icon, color } = getEventDisplay(event.type);

  return (
    <div className="flex items-start gap-3 py-2 px-3 rounded-lg hover:bg-bg-secondary transition-colors">
      <div className={cn('mt-0.5', color)}>
        <Icon className="w-4 h-4" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm text-text-primary break-words whitespace-normal">
          {event.message}
        </p>
        {event.agent && (
          <p className="text-xs text-text-secondary mt-0.5">{event.agent}</p>
        )}
      </div>
      {showTimestamp && (
        <span className="text-xs text-text-muted whitespace-nowrap">
          {formatRelativeTime(event.timestamp)}
        </span>
      )}
    </div>
  );
}

function getEventDisplay(type: EventType): { icon: typeof Rocket; color: string } {
  switch (type) {
    case 'job_created':
      return { icon: Rocket, color: 'text-primary-500' };
    case 'stage_started':
      return { icon: PlayCircle, color: 'text-info-500' };
    case 'stage_completed':
      return { icon: CheckCircle, color: 'text-success-500' };
    case 'hitl_requested':
      return { icon: AlertCircle, color: 'text-warning-500' };
    case 'agent_event':
      return { icon: Clock, color: 'text-info-500' };
    case 'job_failed':
    case 'task_failed':
    case 'failed':
    case 'job_aborted':
      return { icon: XCircle, color: 'text-error-500' };
    case 'approved':
      return { icon: ThumbsUp, color: 'text-success-500' };
    case 'rejected':
      return { icon: ThumbsDown, color: 'text-warning-500' };
    default:
      return { icon: Clock, color: 'text-text-muted' };
  }
}
