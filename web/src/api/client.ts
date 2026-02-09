import type { Artifact, ArtifactType, Job } from '../types';

const API_BASE = '/api';

export class ApiError extends Error {
  status: number;
  data?: unknown;

  constructor(status: number, message: string, data?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const data = await response.json().catch(() => null);
    throw new ApiError(
      response.status,
      data?.detail || data?.message || response.statusText,
      data
    );
  }
  return response.json();
}

export const api = {
  // Projects
  async createProject(data: { project_id: string; requirements: string; metadata?: Record<string, unknown> }) {
    const response = await fetch(`${API_BASE}/projects/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      cache: 'no-store',
      body: JSON.stringify(data),
    });
    return handleResponse<{ job_id: string; project_id: string; status: string }>(response);
  },

  async getJob(jobId: string) {
    const response = await fetch(`${API_BASE}/projects/${jobId}`, { cache: 'no-store' });
    return handleResponse<Job>(response);
  },

  async getJobs(limit = 50) {
    const response = await fetch(`${API_BASE}/projects/?limit=${limit}`, { cache: 'no-store' });
    return handleResponse<{ jobs: Job[] }>(response);
  },

  async deleteJob(jobId: string) {
    const response = await fetch(`${API_BASE}/projects/${jobId}`, {
      method: 'DELETE',
    });
    return handleResponse<{ message: string }>(response);
  },

  async getPrd(jobId: string) {
    const response = await fetch(`${API_BASE}/projects/${jobId}/prd`, { cache: 'no-store' });
    return handleResponse<{
      content: string;
      artifact_id: string;
      created_at: string;
      memory_hits?: Array<{ id: string; score: number }>;
    }>(response);
  },

  async getPlan(jobId: string) {
    const response = await fetch(`${API_BASE}/projects/${jobId}/plan`, { cache: 'no-store' });
    return handleResponse<{
      content: string;
      artifact_id: string;
      created_at: string;
    }>(response);
  },

  async getJobUsage(jobId: string) {
    // Prevent browser/proxy caching; this endpoint is expected to change while a job runs.
    // Use a cache-buster query param in addition to `cache: 'no-store'` for extra safety.
    const response = await fetch(`${API_BASE}/projects/${jobId}/usage?ts=${Date.now()}`, {
      cache: 'no-store',
    });
    return handleResponse<{
      job_id: string;
      usage: {
        input_tokens: number;
        output_tokens: number;
        total_tokens: number;
        calls: number;
        cost_usd: number | null;
        cost_available?: boolean;
      };
    }>(response);
  },

  async getArtifacts(jobId: string) {
    const response = await fetch(`${API_BASE}/artifacts/job/${jobId}`, { cache: 'no-store' });
    const data = await handleResponse<{
      artifacts: Array<{
        artifact_id?: string;
        artifact_type?: string;
        id?: string;
        type?: string;
        content?: string;
        created_at?: string;
        updated_at?: string;
        metadata?: Record<string, unknown>;
      }>;
    }>(response);

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

    const isArtifactType = (value: string): value is ArtifactType =>
      ARTIFACT_TYPES.includes(value as ArtifactType);

    const normalizeType = (type?: string): ArtifactType => {
      if (!type) return 'documentation';
      if (type === 'ui_ux') type = 'uiux';
      if (type === 'support_docs') type = 'support';
      return isArtifactType(type) ? type : 'documentation';
    };

    return {
      artifacts: (data.artifacts || []).map(
        (artifact): Artifact => ({
          artifact_id: artifact.artifact_id ?? artifact.id ?? '',
          job_id: jobId,
          artifact_type: normalizeType(artifact.artifact_type ?? artifact.type),
          content: artifact.content ?? '',
          created_at: artifact.created_at ?? artifact.updated_at ?? '',
          metadata: artifact.metadata,
        })
      ),
    };
  },

  async approvePrd(jobId: string, notes?: string) {
    const response = await fetch(`${API_BASE}/projects/${jobId}/approve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ approved: true, notes }),
    });
    return handleResponse<{ status: string; message: string }>(response);
  },

  async requestChanges(jobId: string, notes: string) {
    const response = await fetch(`${API_BASE}/projects/${jobId}/request_changes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ notes }),
    });
    return handleResponse<{ status: string; message: string }>(response);
  },

  async restartJob(jobId: string) {
    const response = await fetch(`${API_BASE}/projects/${jobId}/restart`, {
      method: 'POST',
    });
    return handleResponse<{ job_id: string; status: string }>(response);
  },

  async cancelJob(jobId: string, reason?: string) {
    const response = await fetch(`${API_BASE}/projects/${jobId}/cancel`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reason }),
    });
    return handleResponse<{ job_id: string; status: string }>(response);
  },

  // Memory / Patterns
  async queryPatterns(query: string, topK = 5, patternType?: string) {
    const response = await fetch(`${API_BASE}/patterns/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, top_k: topK, pattern_type: patternType }),
    });
    // Backend returns { results: [...] }. Keep a stable { patterns: [...] } shape for UI code.
    const data = await handleResponse<{
      results?: Array<{
        id: string;
        text: string;
        score: number;
        metadata?: Record<string, unknown>;
      }>;
      patterns?: Array<{
        id: string;
        text: string;
        score: number;
        metadata?: Record<string, unknown>;
      }>;
    }>(response);
    return { patterns: data.patterns ?? data.results ?? [] };
  },

  async getSuggestions(requirements: string) {
    const response = await fetch(`${API_BASE}/patterns/suggest`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ requirements }),
    });
    // Backend returns { suggestions: [{ pattern_id, text, similarity_score, combined_score, metadata, ... }] }.
    // Normalize to a stable UI-friendly shape.
    const data = await handleResponse<{
      suggestions?: Array<{
        pattern_id?: string;
        text?: string;
        combined_score?: number;
        similarity_score?: number;
        metadata?: Record<string, unknown>;
      }>;
    }>(response);
    return {
      suggestions: (data.suggestions ?? []).map((s) => ({
        id: s.pattern_id ?? '',
        text: s.text ?? '',
        score: s.combined_score ?? s.similarity_score ?? 0,
        pattern_type: (s.metadata?.pattern_type as string | undefined) ?? 'template',
        metadata: s.metadata,
      })),
    };
  },

  // Export
  async exportProject(jobId: string) {
    const response = await fetch(`${API_BASE}/projects/${jobId}/export`);
    if (!response.ok) {
      throw new ApiError(response.status, 'Export failed');
    }
    return response.blob();
  },

  // Health
  async getHealth() {
    const response = await fetch(`${API_BASE.replace('/api', '')}/health`);
    return handleResponse<{ status: string }>(response);
  },
};

// SSE Event Stream
export function createEventSource(jobId?: string): EventSource {
  // Use direct connection to API for SSE (bypass Vite proxy which may buffer)
  const sseBase = import.meta.env.VITE_API_URL || 'http://localhost:8000';
  const url = jobId
    ? `${sseBase}/api/events/stream?job_id=${jobId}`
    : `${sseBase}/api/events/stream`;
  return new EventSource(url);
}
