// Job and Project types
export interface Job {
  job_id: string;
  project_id: string;
  status: JobStatus;
  stage: WorkflowStage;
  created_at: string;
  updated_at: string;
  metadata?: Record<string, unknown>;
}

export type JobStatus =
  | 'queued'
  | 'running'
  | 'in_progress'
  | 'waiting_approval'
  | 'completed'
  | 'failed';

export type WorkflowStage =
  | 'initialization'
  | 'prd_generation'
  | 'waiting_for_approval'
  | 'plan_generation'
  | 'architecture_design'
  | 'uiux_design'
  | 'development'
  | 'qa_testing'
  | 'security_review'
  | 'documentation'
  | 'support_docs'
  | 'pm_review'
  | 'delivery'
  | 'completed'
  | 'failed';

// Artifact types
export interface Artifact {
  artifact_id: string;
  job_id: string;
  artifact_type: ArtifactType;
  content: string;
  created_at: string;
  metadata?: Record<string, unknown>;
}

export type ArtifactType =
  | 'prd'
  | 'plan'
  | 'architecture'
  | 'uiux'
  | 'development'
  | 'qa'
  | 'security'
  | 'documentation'
  | 'support';

// Memory types
export interface MemoryPattern {
  id: string;
  pattern_type: string;
  text: string;
  score: number;
  metadata?: {
    project_id?: string;
    job_id?: string;
    created_at?: string;
    usage_count?: number;
    success_rate?: number;
  };
}

// Event types for SSE
export interface AgentEvent {
  id: string;
  type: EventType;
  message: string;
  timestamp: string;
  agent?: string;
  job_id?: string;
  metadata?: Record<string, unknown>;
}

export type EventType =
  | 'job_created'
  | 'job_started'
  | 'job_completed'
  | 'job_failed'
  | 'stage_started'
  | 'stage_completed'
  | 'task_started'
  | 'task_completed'
  | 'agent_event'
  | 'task_failed'
  | 'hitl_requested'
  | 'approved'
  | 'rejected'
  | 'failed';

// API Request/Response types
export interface CreateProjectRequest {
  project_id: string;
  requirements: string;
  metadata?: Record<string, unknown>;
}

export interface CreateProjectResponse {
  job_id: string;
  project_id: string;
  status: string;
}

export interface ApproveRequest {
  approved: boolean;
  notes?: string;
}

export interface PatternQueryRequest {
  query: string;
  top_k?: number;
  pattern_type?: string;
}

// Component prop types
export interface StageInfo {
  id: WorkflowStage;
  name: string;
  agent: string;
  status: 'pending' | 'active' | 'completed' | 'failed' | 'skipped';
  duration?: number;
  icon: string;
  color: string;
}

// Workflow stage metadata
export const WORKFLOW_STAGES: StageInfo[] = [
  { id: 'initialization', name: 'Init', agent: 'system', status: 'pending', icon: '⚙️', color: 'stage-plan' },
  { id: 'prd_generation', name: 'PRD', agent: 'prd_agent', status: 'pending', icon: '📝', color: 'stage-prd' },
  { id: 'waiting_for_approval', name: 'Approval', agent: 'prd_agent', status: 'pending', icon: '🧾', color: 'stage-prd' },
  { id: 'plan_generation', name: 'Plan', agent: 'plan_agent', status: 'pending', icon: '📋', color: 'stage-plan' },
  { id: 'architecture_design', name: 'Architecture', agent: 'architect_agent', status: 'pending', icon: '🏗️', color: 'stage-arch' },
  { id: 'uiux_design', name: 'UI/UX', agent: 'uiux_agent', status: 'pending', icon: '🎨', color: 'stage-uiux' },
  { id: 'development', name: 'Development', agent: 'developer_agent', status: 'pending', icon: '💻', color: 'stage-dev' },
  { id: 'qa_testing', name: 'QA', agent: 'qa_agent', status: 'pending', icon: '✅', color: 'stage-qa' },
  { id: 'security_review', name: 'Security', agent: 'security_agent', status: 'pending', icon: '🔒', color: 'stage-security' },
  { id: 'documentation', name: 'Docs', agent: 'tech_writer', status: 'pending', icon: '📚', color: 'stage-docs' },
  { id: 'support_docs', name: 'Support', agent: 'support_engineer', status: 'pending', icon: '🧰', color: 'stage-docs' },
  { id: 'pm_review', name: 'PM Review', agent: 'product_manager', status: 'pending', icon: '👔', color: 'stage-prd' },
  { id: 'delivery', name: 'Delivery', agent: 'delivery_agent', status: 'pending', icon: '📦', color: 'stage-dev' },
  { id: 'completed', name: 'Completed', agent: 'system', status: 'pending', icon: '🏁', color: 'stage-qa' },
  { id: 'failed', name: 'Failed', agent: 'system', status: 'pending', icon: '🛑', color: 'stage-security' },
];

// Helper to get stage index
export function getStageIndex(stage: WorkflowStage): number {
  return WORKFLOW_STAGES.findIndex(s => s.id === stage);
}

// Helper to check if stage is complete
export function isStageComplete(currentStage: WorkflowStage, checkStage: WorkflowStage): boolean {
  const currentIndex = getStageIndex(currentStage);
  const checkIndex = getStageIndex(checkStage);
  return checkIndex < currentIndex;
}
