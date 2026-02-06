# Agent Bus UI/UX Design Plan

## 1. Product Overview

### 1.1 Purpose

Agent Bus is an **internal developer tool** that transforms customer requirements into comprehensive software planning documents. Instead of developers rushing to code when a customer request comes in, they use Agent Bus to:

1. **Generate a PRD** from customer requirements
2. **Review and refine** the PRD to ensure alignment with customer needs
3. **Approve** the PRD to trigger automated document generation
4. **Receive complete planning artifacts** for use with AI coding agents

### 1.2 Core Value Proposition

- **Consistency**: Every project follows the same structured planning process
- **Quality**: AI agents generate professional-grade documents
- **Efficiency**: Automated pipeline reduces manual documentation work
- **Learning**: Memory system recognizes patterns and suggests relevant templates
- **Governance**: HITL approval gate ensures human oversight

### 1.3 System Architecture Context

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            USER INTERFACE                                │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐       │
│  │ Submit  │→ │ Review  │→ │ Monitor │→ │ View    │→ │ Export  │       │
│  │ Request │  │ PRD     │  │Progress │  │Artifacts│  │ Docs    │       │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘  └─────────┘       │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                              API SERVICE                                 │
│  FastAPI · REST Endpoints · SSE Events · Authentication                 │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
            ┌──────────────┐ ┌──────────┐ ┌────────────────┐
            │ ORCHESTRATOR │ │  REDIS   │ │    WORKERS     │
            │ Master Agent │ │  Queue   │ │ Agent Executor │
            └──────────────┘ └──────────┘ └────────────────┘
                    │                               │
                    └───────────────┬───────────────┘
                                    ▼
            ┌───────────────────────────────────────────────┐
            │               DATA LAYER                       │
            │  ┌────────────┐  ┌─────────┐  ┌───────────┐  │
            │  │ PostgreSQL │  │ChromaDB │  │ Artifacts │  │
            │  │   State    │  │ Memory  │  │  Storage  │  │
            │  └────────────┘  └─────────┘  └───────────┘  │
            └───────────────────────────────────────────────┘
```

---

## 2. User Personas

### 2.1 Primary: Software Engineer

**Role**: Receives customer requests, initiates planning, reviews PRDs

**Goals**:
- Quickly submit customer requirements
- Review and refine generated PRD
- Ensure technical accuracy before approval
- Track progress of document generation
- Download artifacts for use with AI coding tools

**Pain Points**:
- Rushing to code without proper planning
- Inconsistent documentation quality
- Repetitive work on similar projects
- Losing context from past projects

**Key Tasks**:
1. Submit new project requirements (2-5 min)
2. Review and approve PRD (10-20 min)
3. Monitor pipeline progress (passive)
4. Download and use generated documents

### 2.2 Secondary: Tech Lead / Architect

**Role**: Reviews architecture and technical decisions

**Goals**:
- Ensure architectural consistency
- Review technical constraints
- Validate security considerations
- Compare with past architectural patterns

**Key Tasks**:
1. Review architecture artifacts
2. Search memory for similar patterns
3. Export technical documentation

### 2.3 Tertiary: Engineering Manager

**Role**: Oversees project pipeline, tracks metrics

**Goals**:
- Monitor team throughput
- Track approval rates
- Identify bottlenecks
- View system health

**Key Tasks**:
1. View dashboard metrics
2. Track active projects
3. Review failed jobs

---

## 3. User Flows

### 3.1 Primary Flow: Customer Request to Documents

```
┌──────────────────────────────────────────────────────────────────────────┐
│                     CUSTOMER REQUEST TO DOCUMENTS                         │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  [1. SUBMIT]     [2. GENERATE]    [3. REVIEW]     [4. APPROVE]          │
│  ┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐           │
│  │Customer │ ──▶ │   PRD   │ ──▶ │Engineer │ ──▶ │  HITL   │           │
│  │ Request │     │  Agent  │     │ Reviews │     │  Gate   │           │
│  └─────────┘     └─────────┘     └─────────┘     └─────────┘           │
│       │               │               │               │                 │
│       ▼               ▼               ▼               ▼                 │
│  ┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐           │
│  │  Form   │     │ Memory  │     │  Edit   │     │ Approve │           │
│  │  Input  │     │ Lookup  │     │ Request │     │ Reject  │           │
│  └─────────┘     └─────────┘     └─────────┘     └─────────┘           │
│                                                       │                 │
│                                                       ▼                 │
│  [5. PIPELINE]                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  Plan ──▶ Architecture ──▶ UI/UX ──▶ Development ──▶ ┌─────────┐ │  │
│  │                                                       │ QA      │ │  │
│  │                                                       │Security │ │  │
│  │                                                       │ Docs    │ │  │
│  │                                                       │Support  │ │  │
│  │                                                       └────┬────┘ │  │
│  │                                                            │      │  │
│  │                                    PM Review ◀─────────────┘      │  │
│  │                                        │                          │  │
│  │                                        ▼                          │  │
│  │                                    Delivery                       │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                       │                 │
│                                                       ▼                 │
│  [6. COMPLETE]                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Download All Artifacts · Use with AI Coding Agents             │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Memory-Assisted Flow

```
┌──────────────────────────────────────────────────────────────────────────┐
│                     MEMORY-ASSISTED WORKFLOW                              │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  1. Engineer types requirements                                          │
│     ┌────────────────────────────────────────────┐                      │
│     │ "Build a REST API with JWT auth..."        │                      │
│     └────────────────────────────────────────────┘                      │
│                          │                                               │
│                          ▼                                               │
│  2. System queries ChromaDB for similar patterns                        │
│     ┌────────────────────────────────────────────┐                      │
│     │ SELECT * FROM memory                       │                      │
│     │ WHERE semantic_similarity > 0.7            │                      │
│     └────────────────────────────────────────────┘                      │
│                          │                                               │
│                          ▼                                               │
│  3. UI shows relevant past projects                                     │
│     ┌────────────────────────────────────────────┐                      │
│     │ Similar Projects:                          │                      │
│     │ • Auth Service v2 (94% match) [Use]        │                      │
│     │ • User API Gateway (87% match) [Use]       │                      │
│     │ • Token Service (82% match) [Use]          │                      │
│     └────────────────────────────────────────────┘                      │
│                          │                                               │
│                          ▼                                               │
│  4. Engineer can adopt patterns from past PRDs                          │
│     ┌────────────────────────────────────────────┐                      │
│     │ PRD now includes proven patterns from      │                      │
│     │ similar successful projects                │                      │
│     └────────────────────────────────────────────┘                      │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### 3.3 HITL Approval Decision Tree

```
                    ┌─────────────────┐
                    │  PRD Generated  │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ Engineer Review │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
       ┌───────────┐  ┌───────────┐  ┌───────────┐
       │  Approve  │  │  Request  │  │  Reject   │
       │           │  │  Changes  │  │  (Cancel) │
       └─────┬─────┘  └─────┬─────┘  └─────┬─────┘
             │              │              │
             ▼              ▼              ▼
       ┌───────────┐  ┌───────────┐  ┌───────────┐
       │ Continue  │  │Regenerate │  │  Archive  │
       │ Pipeline  │  │   PRD     │  │   Job     │
       └───────────┘  └───────────┘  └───────────┘
```

---

## 4. Design System

### 4.1 Design Principles

1. **Developer-First**: Clean, information-dense interface suitable for technical users
2. **Progressive Disclosure**: Show essentials first, details on demand
3. **Status Visibility**: Always show what agents are doing and why
4. **Memory Integration**: Surface relevant patterns at every decision point
5. **Keyboard-Friendly**: Power users can navigate without mouse

### 4.2 Color Palette

#### Light Mode (Default)
```css
/* Brand */
--color-primary-500: #3b82f6;    /* Blue - primary actions */
--color-primary-600: #2563eb;    /* Blue - hover state */
--color-primary-700: #1d4ed8;    /* Blue - active state */

/* Semantic */
--color-success-500: #22c55e;    /* Green - approved, completed */
--color-warning-500: #f59e0b;    /* Amber - pending review, caution */
--color-error-500: #ef4444;      /* Red - failed, rejected */
--color-info-500: #06b6d4;       /* Cyan - informational */

/* Workflow Stages */
--color-stage-prd: #8b5cf6;      /* Purple - PRD generation */
--color-stage-plan: #ec4899;     /* Pink - Planning */
--color-stage-arch: #f97316;     /* Orange - Architecture */
--color-stage-uiux: #14b8a6;     /* Teal - UI/UX Design */
--color-stage-dev: #3b82f6;      /* Blue - Development */
--color-stage-qa: #22c55e;       /* Green - QA */
--color-stage-security: #ef4444; /* Red - Security */
--color-stage-docs: #6366f1;     /* Indigo - Documentation */

/* Neutral */
--color-bg-primary: #ffffff;
--color-bg-secondary: #f9fafb;
--color-bg-tertiary: #f3f4f6;
--color-text-primary: #111827;
--color-text-secondary: #6b7280;
--color-text-muted: #9ca3af;
--color-border: #e5e7eb;
```

#### Dark Mode
Dark mode is intentionally **not supported**. The UI is light-theme only to ensure consistency across planning artifacts and exported visuals.

#### Theme Enforcement
- Use the design tokens from `web/src/styles/tokens.css` for all colors.
- Avoid Tailwind default palette colors (e.g., `gray-`, `blue-`) and raw hex values in UI code.
- `npm run lint` includes a theme check that blocks non-token colors in `web/src`.

### 4.3 Typography

```css
/* Font Stack */
--font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
--font-mono: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;

/* Scale */
--text-xs: 0.75rem;     /* 12px - labels, badges */
--text-sm: 0.875rem;    /* 14px - secondary text, table cells */
--text-base: 1rem;      /* 16px - body text */
--text-lg: 1.125rem;    /* 18px - emphasized text */
--text-xl: 1.25rem;     /* 20px - section headers */
--text-2xl: 1.5rem;     /* 24px - page titles */
--text-3xl: 1.875rem;   /* 30px - hero text */

/* Weights */
--font-normal: 400;
--font-medium: 500;
--font-semibold: 600;
--font-bold: 700;
```

### 4.4 Spacing

```css
/* 4px base unit */
--space-1: 0.25rem;   /* 4px */
--space-2: 0.5rem;    /* 8px */
--space-3: 0.75rem;   /* 12px */
--space-4: 1rem;      /* 16px */
--space-5: 1.25rem;   /* 20px */
--space-6: 1.5rem;    /* 24px */
--space-8: 2rem;      /* 32px */
--space-10: 2.5rem;   /* 40px */
--space-12: 3rem;     /* 48px */
--space-16: 4rem;     /* 64px */
```

### 4.5 Breakpoints

```css
--bp-sm: 640px;    /* Mobile landscape */
--bp-md: 768px;    /* Tablet */
--bp-lg: 1024px;   /* Desktop */
--bp-xl: 1280px;   /* Large desktop */
--bp-2xl: 1536px;  /* Extra large */
```

### 4.6 Shadows & Borders

```css
/* Shadows */
--shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
--shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1);
--shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1);

/* Border Radius */
--radius-sm: 4px;
--radius-md: 6px;
--radius-lg: 8px;
--radius-xl: 12px;
--radius-full: 9999px;
```

---

## 5. Component Library

### 5.1 Core Components

#### Button
```typescript
interface ButtonProps {
  variant: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger';
  size: 'sm' | 'md' | 'lg';
  loading?: boolean;
  disabled?: boolean;
  icon?: ReactNode;
  fullWidth?: boolean;
}

/* States: default → hover → active → focus → disabled → loading */
```

#### Input / Textarea
```typescript
interface InputProps {
  label: string;
  hint?: string;
  error?: string;
  required?: boolean;
  charCount?: { current: number; min?: number; max?: number };
}

/* States: default → focus → error → disabled */
/* Features: inline validation, character counter */
```

#### Card
```typescript
interface CardProps {
  variant: 'default' | 'elevated' | 'outlined' | 'interactive';
  padding: 'none' | 'sm' | 'md' | 'lg';
  onClick?: () => void;
}
```

#### Badge / Status
```typescript
interface BadgeProps {
  variant: 'default' | 'success' | 'warning' | 'error' | 'info';
  size: 'sm' | 'md';
  dot?: boolean;      /* Show status dot */
  pulse?: boolean;    /* Animate for active states */
}
```

#### Modal / Dialog
```typescript
interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  size: 'sm' | 'md' | 'lg' | 'xl' | 'full';
  footer?: ReactNode;
}

/* Sub-types: ConfirmDialog, AlertDialog */
```

#### Toast / Notification
```typescript
interface ToastProps {
  type: 'success' | 'error' | 'warning' | 'info';
  title: string;
  description?: string;
  duration?: number;   /* ms, 0 for persistent */
  action?: { label: string; onClick: () => void };
}

/* Position: top-right */
/* Animation: slide in from right */
```

### 5.2 Domain Components

#### WorkflowProgress
```typescript
interface WorkflowProgressProps {
  stages: {
    id: string;
    name: string;
    status: 'pending' | 'active' | 'completed' | 'failed' | 'skipped';
    agent: string;
    duration?: number;
  }[];
  currentStage: string;
  orientation: 'horizontal' | 'vertical';
}

/* Visual: Connected nodes with stage colors */
/* Animation: Pulse on active stage */
```

#### AgentStatusCard
```typescript
interface AgentStatusCardProps {
  agentId: string;
  agentName: string;
  agentIcon: string;    /* Emoji or icon */
  status: 'idle' | 'working' | 'completed' | 'failed';
  task?: string;
  elapsed?: number;
  outputPreview?: string;
}

/* Shows: Agent avatar, current task, progress */
/* Animation: Spinner when working */
```

#### MemoryHitCard
```typescript
interface MemoryHitCardProps {
  patternId: string;
  patternType: 'prd' | 'architecture' | 'plan' | 'code';
  title: string;
  similarity: number;   /* 0-1 */
  successRate?: number; /* Historical success */
  usageCount: number;
  preview: string;
  onUseTemplate: () => void;
  onViewDetails: () => void;
}

/* Shows: Match score, preview snippet, use button */
```

#### ArtifactViewer
```typescript
interface ArtifactViewerProps {
  type: 'prd' | 'plan' | 'architecture' | 'uiux' | 'development' |
        'qa' | 'security' | 'documentation' | 'support';
  content: string;
  format: 'markdown' | 'json';
  sections?: string[];  /* For tabbed navigation */
  memoryHits?: MemoryHit[];
  onApprove?: () => void;
  onRequestChanges?: (notes: string) => void;
}

/* Features: Markdown render, syntax highlight, copy, download */
```

#### ActivityFeed
```typescript
interface ActivityFeedProps {
  events: {
    id: string;
    type: 'job_created' | 'stage_started' | 'stage_completed' |
          'hitl_requested' | 'approved' | 'rejected' | 'failed';
    message: string;
    timestamp: Date;
    agent?: string;
    metadata?: Record<string, any>;
  }[];
  maxItems?: number;
  autoScroll?: boolean;
}

/* Animation: New events slide in */
```

---

## 6. Page Layouts

### 6.1 Dashboard (Home)

**Route**: `/` or `/ui/`

**Purpose**: Quick project submission, active project overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ [Logo] Agent Bus           [Memory] [Metrics] [Settings] [User] │   │
│  └─────────────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │                    + Create New Project                            │ │
│  │  ─────────────────────────────────────────────────────────────── │ │
│  │  Transform customer requirements into complete planning docs      │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│  ┌─── Quick Stats ──────────────────────────────────────────────────┐ │
│  │ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐             │ │
│  │ │    5     │ │    2     │ │   89%    │ │   32m    │             │ │
│  │ │ Active   │ │ Pending  │ │ Approval │ │ Avg Time │             │ │
│  │ │ Projects │ │ Review   │ │ Rate     │ │          │             │ │
│  │ └──────────┘ └──────────┘ └──────────┘ └──────────┘             │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│  ┌─── Pending Your Review ──────────────────────────────────────────┐ │
│  │                                                                   │ │
│  │  ⚠️ payment-gateway-v2          PRD Ready for Review    [Review] │ │
│  │  ⚠️ user-auth-service           PRD Ready for Review    [Review] │ │
│  │                                                                   │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│  ┌─── Active Projects ──────────────────────────────────────────────┐ │
│  │                                                                   │ │
│  │  ┌───────────────────┐  ┌───────────────────┐  ┌──────────────┐ │ │
│  │  │ analytics-dash    │  │ mobile-api        │  │ crm-sync     │ │ │
│  │  │ ████████░░ 75%    │  │ ██████░░░░ 55%    │  │ ████░░░░░░ 40%│ │ │
│  │  │ Development       │  │ Architecture      │  │ Plan Gen     │ │ │
│  │  │ 12m elapsed       │  │ 8m elapsed        │  │ 5m elapsed   │ │ │
│  │  └───────────────────┘  └───────────────────┘  └──────────────┘ │ │
│  │                                                                   │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│  ┌─── Recent Completed ─────────────────────────────────────────────┐ │
│  │                                                                   │ │
│  │  ✓ inventory-system       Completed 2h ago      [View Artifacts] │ │
│  │  ✓ notification-service   Completed 5h ago      [View Artifacts] │ │
│  │  ✓ reporting-module       Completed 1d ago      [View Artifacts] │ │
│  │                                                                   │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**States**:
| State | Visual |
|-------|--------|
| Loading | Skeleton cards, shimmer stats |
| Empty | "No projects yet" + prominent Create button |
| Error | Error banner with retry, show cached data |
| Degraded | Warning banner, limited functionality |

### 6.2 Create Project

**Route**: `/ui/new` or `/ui/create`

**Purpose**: Submit customer requirements with memory-assisted suggestions

```
┌─────────────────────────────────────────────────────────────────────────┐
│  ← Back to Dashboard                                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Create New Project                                                     │
│  Transform customer requirements into comprehensive planning documents  │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │                                                                   │ │
│  │  Project ID *                                                     │ │
│  │  ┌─────────────────────────────────────────────────────────────┐ │ │
│  │  │ e.g., payment-gateway-v2                                    │ │ │
│  │  └─────────────────────────────────────────────────────────────┘ │ │
│  │  Use lowercase letters, numbers, and hyphens                      │ │
│  │                                                                   │ │
│  │  Customer Requirements *                                          │ │
│  │  ┌─────────────────────────────────────────────────────────────┐ │ │
│  │  │                                                             │ │ │
│  │  │ Paste or type the customer requirements here...             │ │ │
│  │  │                                                             │ │ │
│  │  │ Include:                                                    │ │ │
│  │  │ - What the customer wants to build                          │ │ │
│  │  │ - Key features and functionality                            │ │ │
│  │  │ - Any technical constraints or preferences                  │ │ │
│  │  │ - Timeline expectations                                     │ │ │
│  │  │                                                             │ │ │
│  │  │                                                             │ │ │
│  │  └─────────────────────────────────────────────────────────────┘ │ │
│  │  156 / 100 characters minimum                        ✓ Valid     │ │
│  │                                                                   │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│  ┌─── Similar Past Projects (from Memory) ──────────────────────────┐ │
│  │                                                                   │ │
│  │  Typing to search patterns...                                    │ │
│  │                                                                   │ │
│  │  ┌─────────────────────────────────────────────────────────────┐ │ │
│  │  │ 🔷 Payment Processing API                       94% match   │ │ │
│  │  │    "REST API with Stripe integration, webhooks..."         │ │ │
│  │  │    Used 8 times · 100% success rate                        │ │ │
│  │  │                                    [View PRD] [Use Pattern] │ │ │
│  │  └─────────────────────────────────────────────────────────────┘ │ │
│  │  ┌─────────────────────────────────────────────────────────────┐ │ │
│  │  │ 🔷 E-commerce Gateway                           87% match   │ │ │
│  │  │    "Multi-tenant payment system with PCI compliance..."    │ │ │
│  │  │    Used 5 times · 100% success rate                        │ │ │
│  │  │                                    [View PRD] [Use Pattern] │ │ │
│  │  └─────────────────────────────────────────────────────────────┘ │ │
│  │                                                                   │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │                                                                   │ │
│  │  [Cancel]                                   [Create Project →]   │ │
│  │                                                                   │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**States**:
| State | Visual |
|-------|--------|
| Initial | Empty form, placeholder text |
| Typing | Character count updates, memory search triggers after 50+ chars |
| Searching Memory | "Searching patterns..." with spinner |
| Memory Results | Pattern cards with similarity scores |
| No Memory Hits | "No similar projects found. This will create new patterns." |
| Validation Error | Red border, error message below field |
| Submitting | Button shows spinner, form disabled |
| Success | Redirect to project status with success toast |
| Error | Error message, form remains enabled |

### 6.3 PRD Review (HITL Gate)

**Route**: `/ui/prd/{job_id}`

**Purpose**: Critical approval gate - engineer reviews and approves PRD

```
┌─────────────────────────────────────────────────────────────────────────┐
│  ← Back to Project                                  [Copy] [Download]   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────┬───────────────────────────┐
│  │                                         │                           │
│  │  PRD: payment-gateway-v2                │  Similar Projects         │
│  │  ──────────────────────────────────────│                           │
│  │  Status: ⚠️ Pending Your Review         │  ┌─────────────────────┐ │
│  │                                         │  │ Payment API v1       │ │
│  │  [Overview] [Features] [Technical]      │  │ 94% similar          │ │
│  │  [Timeline] [Success Metrics]           │  │ Completed 3mo ago    │ │
│  │                                         │  │ [Compare]            │ │
│  │  ┌─────────────────────────────────────┐│  └─────────────────────┘ │
│  │  │                                     ││                           │
│  │  │  # Product Requirements Document    ││  ┌─────────────────────┐ │
│  │  │                                     ││  │ Stripe Integration   │ │
│  │  │  ## Executive Summary               ││  │ 87% similar          │ │
│  │  │                                     ││  │ Completed 6mo ago    │ │
│  │  │  Build a modern payment gateway     ││  │ [Compare]            │ │
│  │  │  service that integrates with       ││  └─────────────────────┘ │
│  │  │  multiple payment providers...      ││                           │
│  │  │                                     ││  ───────────────────────  │
│  │  │  ## Problem Statement               ││                           │
│  │  │                                     ││  Memory Hits (3)         │
│  │  │  Current payment processing is      ││                           │
│  │  │  fragmented across multiple...      ││  • JWT Auth Pattern      │
│  │  │                                     ││  • REST API Template     │
│  │  │  ## Goals and Objectives            ││  • PCI Compliance Guide  │
│  │  │                                     ││                           │
│  │  │  1. Unified payment interface       ││                           │
│  │  │  2. Support 5+ providers            ││                           │
│  │  │  3. 99.9% uptime SLA                ││                           │
│  │  │                                     ││                           │
│  │  │  ## User Stories                    ││                           │
│  │  │                                     ││                           │
│  │  │  As a developer, I want to...       ││                           │
│  │  │                                     ││                           │
│  │  └─────────────────────────────────────┘│                           │
│  │                                         │                           │
│  └─────────────────────────────────────────┴───────────────────────────┘
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐
│  │                                                                     │
│  │  Your Decision                                                      │
│  │                                                                     │
│  │  Feedback (optional)                                                │
│  │  ┌─────────────────────────────────────────────────────────────┐   │
│  │  │ Add notes for the team or revision instructions...          │   │
│  │  └─────────────────────────────────────────────────────────────┘   │
│  │                                                                     │
│  │  ┌──────────────────────┐  ┌────────────────────────────────────┐ │
│  │  │ ⚠️ Request Changes    │  │ ✓ Approve & Continue Pipeline     │ │
│  │  │    Regenerate PRD    │  │   Start document generation        │ │
│  │  └──────────────────────┘  └────────────────────────────────────┘ │
│  │                                                                     │
│  └─────────────────────────────────────────────────────────────────────┘
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**States**:
| State | Visual |
|-------|--------|
| Loading | Skeleton content, disabled actions |
| PRD Not Ready | "PRD is being generated..." with progress |
| Review Mode | Full PRD content, actions enabled |
| Submitting Approval | Spinner on button, all disabled |
| Approved | Success toast, redirect to status |
| Changes Requested | Toast, PRD regenerates |
| Already Approved | Read-only view, no actions |
| Failed | Error state with retry option |

**Approval Confirmation Dialog**:
```
┌─────────────────────────────────────────────────┐
│  Approve PRD?                               [×] │
├─────────────────────────────────────────────────┤
│                                                 │
│  This will start the full document pipeline:    │
│                                                 │
│  1. Plan Generation        (~5 min)             │
│  2. Architecture Design    (~10 min)            │
│  3. UI/UX Design           (~5 min)             │
│  4. Development Plan       (~15 min)            │
│  5. QA + Security + Docs   (~10 min parallel)   │
│  6. PM Review + Delivery   (~5 min)             │
│                                                 │
│  Estimated total: 45-60 minutes                 │
│                                                 │
│  ┌─────────────┐    ┌─────────────────────────┐ │
│  │   Cancel    │    │  Yes, Approve & Start   │ │
│  └─────────────┘    └─────────────────────────┘ │
│                                                 │
└─────────────────────────────────────────────────┘
```

### 6.4 Project Status / Progress

**Route**: `/ui/project/{job_id}` or `/ui/status/{job_id}`

**Purpose**: Real-time monitoring of document generation pipeline

```
┌─────────────────────────────────────────────────────────────────────────┐
│  ← Back to Dashboard                                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  payment-gateway-v2                                                     │
│  Status: 🔵 In Progress · Started 12 minutes ago                        │
│                                                                         │
│  ┌─── Workflow Progress ────────────────────────────────────────────┐  │
│  │                                                                   │  │
│  │  ✓ ━━━ ✓ ━━━ ✓ ━━━ ● ━━━ ○ ━━━ ○ ━━━ ○ ━━━ ○ ━━━ ○ ━━━ ○       │  │
│  │  PRD   Plan  Arch  UI/UX  Dev   QA   Sec  Docs  PM   Done       │  │
│  │                     ↑                                             │  │
│  │                 CURRENT                                           │  │
│  │                                                                   │  │
│  │  Legend: ✓ Complete  ● In Progress  ○ Pending                    │  │
│  │                                                                   │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ┌─── Current Stage ────────────────────────────────────────────────┐  │
│  │                                                                   │  │
│  │  🎨 UI/UX Agent                                                   │  │
│  │  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 67%          │  │
│  │                                                                   │  │
│  │  Generating design system and component specifications...         │  │
│  │  ⏱️ 2m 15s elapsed                                                │  │
│  │                                                                   │  │
│  │  ┌─────────────────────────────────────────────────────────────┐ │  │
│  │  │ Preview:                                                    │ │  │
│  │  │ {                                                           │ │  │
│  │  │   "design_system": {                                        │ │  │
│  │  │     "colors": { "primary": "#3b82f6", ... },                │ │  │
│  │  │     "typography": { ... }                                   │ │  │
│  │  │   }                                                         │ │  │
│  │  │ }                                                           │ │  │
│  │  └─────────────────────────────────────────────────────────────┘ │  │
│  │                                                                   │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ┌─── Completed Stages ─────────────────────────────────────────────┐  │
│  │                                                                   │  │
│  │  ✓ PRD Generation          3m 20s    [View PRD]                  │  │
│  │  ✓ Plan Generation         2m 45s    [View Plan]                 │  │
│  │  ✓ Architecture Design     4m 12s    [View Architecture]         │  │
│  │                                                                   │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ┌─── Activity Feed ────────────────────────────────────────────────┐  │
│  │                                                                   │  │
│  │  14:32  🎨 UI/UX Agent started                                   │  │
│  │  14:28  ✓ Architecture Design completed (4m 12s)                 │  │
│  │  14:24  🏗️ Architect Agent started                               │  │
│  │  14:21  ✓ Plan Generation completed (2m 45s)                     │  │
│  │  14:18  📋 Plan Agent started                                    │  │
│  │  14:15  ✓ PRD approved by engineer@company.com                   │  │
│  │  14:12  ⚠️ PRD ready for review                                  │  │
│  │  14:09  ✓ PRD Generation completed (3m 20s)                      │  │
│  │  14:06  📝 PRD Agent started                                     │  │
│  │  14:05  🚀 Job created                                           │  │
│  │                                                                   │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**States**:
| State | Visual |
|-------|--------|
| Loading | Skeleton workflow, skeleton cards |
| Queued | First stage pending, "Waiting to start" |
| In Progress | Pulse on current stage, live timer |
| Waiting Approval | Prominent "Review PRD" CTA |
| Completed | All green checks, "Download All" button |
| Failed | Red X on failed stage, error + retry |
| SSE Disconnected | Yellow banner, manual refresh |

**Parallel Stage Visualization**:
```
                        ┌─────────┐
                    ┌───│   QA    │───┐
                    │   └─────────┘   │
                    │   ┌─────────┐   │
  ┌──────────┐     ├───│Security │───┤     ┌─────────┐
  │   Dev    │─────┤   └─────────┘   ├─────│   PM    │
  └──────────┘     │   ┌─────────┐   │     └─────────┘
                    ├───│  Docs   │───┤
                    │   └─────────┘   │
                    │   ┌─────────┐   │
                    └───│ Support │───┘
                        └─────────┘
```

### 6.5 Deliverables / Artifacts

**Route**: `/ui/project/{job_id}/deliverables` or `/ui/artifacts/{job_id}`

**Purpose**: Download all generated planning documents

```
┌─────────────────────────────────────────────────────────────────────────┐
│  ← Back to Project                                                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Project Deliverables                                                   │
│  payment-gateway-v2 · Completed 45 minutes ago                          │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐
│  │                     [⬇️ Download All as ZIP]                        │
│  │               All documents ready for AI coding agents              │
│  └─────────────────────────────────────────────────────────────────────┘
│                                                                         │
│  ┌─── Planning Documents ───────────────────────────────────────────┐  │
│  │                                                                   │  │
│  │  ┌─────────────────────────────────────────────────────────────┐ │  │
│  │  │  📄 Product Requirements Document (PRD)                     │ │  │
│  │  │     Generated 40m ago · 8.2 KB · Markdown                   │ │  │
│  │  │     Executive summary, user stories, requirements           │ │  │
│  │  │                                         [View] [Download]   │ │  │
│  │  └─────────────────────────────────────────────────────────────┘ │  │
│  │                                                                   │  │
│  │  ┌─────────────────────────────────────────────────────────────┐ │  │
│  │  │  📋 Project Plan                                            │ │  │
│  │  │     Generated 37m ago · 5.1 KB · Markdown                   │ │  │
│  │  │     Milestones, tasks, dependencies, timeline               │ │  │
│  │  │                                         [View] [Download]   │ │  │
│  │  └─────────────────────────────────────────────────────────────┘ │  │
│  │                                                                   │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ┌─── Technical Documents ──────────────────────────────────────────┐  │
│  │                                                                   │  │
│  │  ┌─────────────────────────────────────────────────────────────┐ │  │
│  │  │  🏗️ System Architecture                                     │ │  │
│  │  │     Generated 33m ago · 12.4 KB · Markdown                  │ │  │
│  │  │     Components, data flow, API contracts, infrastructure    │ │  │
│  │  │                                         [View] [Download]   │ │  │
│  │  └─────────────────────────────────────────────────────────────┘ │  │
│  │                                                                   │  │
│  │  ┌─────────────────────────────────────────────────────────────┐ │  │
│  │  │  🎨 UI/UX Design System                                     │ │  │
│  │  │     Generated 28m ago · 6.8 KB · JSON                       │ │  │
│  │  │     Colors, typography, components, layouts                 │ │  │
│  │  │                                         [View] [Download]   │ │  │
│  │  └─────────────────────────────────────────────────────────────┘ │  │
│  │                                                                   │  │
│  │  ┌─────────────────────────────────────────────────────────────┐ │  │
│  │  │  💻 Development Plan                                        │ │  │
│  │  │     Generated 20m ago · 15.2 KB · Markdown                  │ │  │
│  │  │     Implementation guide, TDD strategy, code structure      │ │  │
│  │  │                                         [View] [Download]   │ │  │
│  │  └─────────────────────────────────────────────────────────────┘ │  │
│  │                                                                   │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ┌─── Quality & Support ────────────────────────────────────────────┐  │
│  │                                                                   │  │
│  │  ┌────────────────┐ ┌────────────────┐ ┌────────────────┐       │  │
│  │  │ ✅ QA Plan     │ │ 🔒 Security    │ │ 📚 Tech Docs   │       │  │
│  │  │ Test strategy  │ │ Review report  │ │ API reference  │       │  │
│  │  │ [View] [⬇️]    │ │ [View] [⬇️]    │ │ [View] [⬇️]    │       │  │
│  │  └────────────────┘ └────────────────┘ └────────────────┘       │  │
│  │                                                                   │  │
│  │  ┌────────────────┐                                              │  │
│  │  │ 🎧 Support Doc │                                              │  │
│  │  │ FAQ, runbooks  │                                              │  │
│  │  │ [View] [⬇️]    │                                              │  │
│  │  └────────────────┘                                              │  │
│  │                                                                   │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 6.6 Memory Explorer

**Route**: `/ui/memory`

**Purpose**: Search and browse patterns from past projects

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Agent Bus · Memory Explorer                                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐
│  │  🔍 Search patterns across all projects...                          │
│  └─────────────────────────────────────────────────────────────────────┘
│                                                                         │
│  Filter by type:                                                        │
│  [All] [PRD] [Architecture] [Plan] [Development] [QA] [Security]       │
│                                                                         │
│  ┌─── Results (47 patterns) ────────────────────────────────────────┐  │
│  │                                                                   │  │
│  │  ┌─────────────────────────────────────────────────────────────┐ │  │
│  │  │  📄 Payment Processing PRD                                  │ │  │
│  │  │     Type: prd · Similarity: 94% · Used 12 times             │ │  │
│  │  │     ──────────────────────────────────────────────────────  │ │  │
│  │  │     "Comprehensive payment gateway with multi-provider      │ │  │
│  │  │     support, PCI compliance, and webhook handling..."       │ │  │
│  │  │                                                             │ │  │
│  │  │     Project: payment-api-v1 · Completed 3 months ago        │ │  │
│  │  │                                [View Full] [Use as Template]│ │  │
│  │  └─────────────────────────────────────────────────────────────┘ │  │
│  │                                                                   │  │
│  │  ┌─────────────────────────────────────────────────────────────┐ │  │
│  │  │  🏗️ Microservices Architecture                              │ │  │
│  │  │     Type: architecture · Similarity: 87% · Used 8 times     │ │  │
│  │  │     ──────────────────────────────────────────────────────  │ │  │
│  │  │     "Event-driven microservices with CQRS, message queues,  │ │  │
│  │  │     and distributed tracing..."                             │ │  │
│  │  │                                                             │ │  │
│  │  │     Project: order-service · Completed 6 months ago         │ │  │
│  │  │                                [View Full] [Use as Template]│ │  │
│  │  └─────────────────────────────────────────────────────────────┘ │  │
│  │                                                                   │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ┌─── Popular Templates ────────────────────────────────────────────┐  │
│  │                                                                   │  │
│  │  Most Used This Month:                                           │  │
│  │  • REST API Template (23 uses)                                   │  │
│  │  • React Dashboard PRD (18 uses)                                 │  │
│  │  • Authentication Architecture (15 uses)                         │  │
│  │  • CRUD Service Plan (12 uses)                                   │  │
│  │                                                                   │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 6.7 Metrics Dashboard

**Route**: `/ui/metrics`

**Purpose**: System health and usage statistics

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Agent Bus · Metrics                                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─── Overview (Last 7 Days) ───────────────────────────────────────┐  │
│  │                                                                   │  │
│  │  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐        │  │
│  │  │    47     │ │    89%    │ │   42min   │ │    94%    │        │  │
│  │  │ Projects  │ │ Approval  │ │ Avg Time  │ │ Success   │        │  │
│  │  │ Completed │ │ Rate      │ │ to Done   │ │ Rate      │        │  │
│  │  └───────────┘ └───────────┘ └───────────┘ └───────────┘        │  │
│  │                                                                   │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ┌─── Projects Over Time ───────────────────────────────────────────┐  │
│  │                                                                   │  │
│  │  12 ┤                                              ╭───╮         │  │
│  │  10 ┤                              ╭───╮     ╭────╯   │         │  │
│  │   8 ┤              ╭───╮     ╭────╯   ╰────╯         │         │  │
│  │   6 ┤        ╭────╯   ╰────╯                         │         │  │
│  │   4 ┤   ╭───╯                                        │         │  │
│  │   2 ┤───╯                                            │         │  │
│  │   0 ┼────────────────────────────────────────────────┘         │  │
│  │      Mon  Tue  Wed  Thu  Fri  Sat  Sun                          │  │
│  │                                                                   │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ┌─── Agent Performance ────────────────────────────────────────────┐  │
│  │                                                                   │  │
│  │  Agent              Avg Time    Success    Jobs                  │  │
│  │  ─────────────────────────────────────────────────               │  │
│  │  📝 PRD Agent       3m 20s      99%        47                    │  │
│  │  📋 Plan Agent      2m 45s      99%        42                    │  │
│  │  🏗️ Architect       4m 12s      98%        42                    │  │
│  │  🎨 UI/UX Agent     3m 08s      100%       42                    │  │
│  │  💻 Developer       7m 30s      97%        42                    │  │
│  │  ✅ QA Agent        3m 45s      99%        42                    │  │
│  │  🔒 Security        2m 55s      100%       42                    │  │
│  │  📚 Tech Writer     4m 20s      99%        42                    │  │
│  │                                                                   │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ┌─── Memory Usage ─────────────────────────────────────────────────┐  │
│  │                                                                   │  │
│  │  Patterns Stored: 1,247                                          │  │
│  │  Memory Queries This Week: 892                                   │  │
│  │  Template Reuse Rate: 34%                                        │  │
│  │  Avg Similarity Score: 0.78                                      │  │
│  │                                                                   │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 7. State Specifications

### 7.1 Loading States

| Component | Loading Visual |
|-----------|----------------|
| Page | Full skeleton with shimmer effect |
| Card | Gray placeholder boxes |
| Table | Skeleton rows (5 rows default) |
| Text | Gray bars of varying widths |
| Button | Spinner icon, text changes to "Loading..." |
| Charts | Shimmer animation on chart area |

### 7.2 Empty States

| Context | Message | Action |
|---------|---------|--------|
| No projects | "No projects yet" | "Create your first project" button |
| No search results | "No patterns found" | "Try different keywords" suggestion |
| No activity | "No recent activity" | Link to create project |
| No artifacts | "Documents still generating" | Link to status page |
| No memory hits | "No similar projects" | "This will create new patterns" info |

### 7.3 Error States

| Error Type | Visual | Action |
|------------|--------|--------|
| API Error | Red banner with message | Retry button |
| Validation Error | Red border + inline message | Fix and retry |
| Network Error | "Connection lost" banner | Auto-retry with countdown |
| Auth Error | Redirect to login | - |
| 404 Not Found | "Project not found" page | Link to dashboard |
| Agent Failure | Red stage indicator + error | Retry or skip options |

### 7.4 Success States

| Action | Feedback |
|--------|----------|
| Project created | Green toast + redirect to status |
| PRD approved | Green toast + "Pipeline started" |
| Download complete | Green toast + file saves |
| Pattern saved | Green toast |

---

## 8. Micro-Interactions & Animations

### 8.1 Animation Tokens

```css
/* Durations */
--duration-fast: 150ms;
--duration-normal: 250ms;
--duration-slow: 400ms;

/* Easings */
--ease-out: cubic-bezier(0.0, 0.0, 0.2, 1);
--ease-in-out: cubic-bezier(0.4, 0, 0.2, 1);
--ease-bounce: cubic-bezier(0.68, -0.55, 0.265, 1.55);
```

### 8.2 Component Animations

| Component | Trigger | Animation |
|-----------|---------|-----------|
| Button | Hover | Scale 1.02, shadow increase |
| Button | Click | Scale 0.98 spring |
| Button | Loading | Spinner fade in |
| Card | Hover | Subtle lift (translateY -2px) |
| Modal | Open | Fade overlay + scale content |
| Modal | Close | Reverse of open |
| Toast | Enter | Slide from right |
| Toast | Exit | Slide to right + fade |
| Workflow Stage | Complete | Checkmark draw |
| Workflow Stage | Active | Pulse animation |
| Workflow Stage | Failed | Shake |
| Activity Item | Enter | Slide from right |
| Skeleton | Loading | Shimmer gradient |

### 8.3 Page Transitions

```typescript
const pageTransition = {
  initial: { opacity: 0, y: 10 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -10 },
  transition: { duration: 0.2 }
};
```

---

## 9. Accessibility

### 9.1 WCAG 2.1 AA Compliance

| Criterion | Implementation |
|-----------|----------------|
| Color Contrast | 4.5:1 minimum for text |
| Focus Visible | 2px ring on all interactive elements |
| Keyboard Navigation | Tab through all actions |
| Screen Reader | ARIA labels, live regions |
| Motion | Respect prefers-reduced-motion |

### 9.2 Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `n` | New project |
| `j` | Jobs list |
| `m` | Memory explorer |
| `/` | Focus search |
| `Esc` | Close modal |
| `Enter` | Submit form |

### 9.3 Screen Reader Announcements

```typescript
// Announce dynamic content
announce("Project created successfully", "polite");
announce("PRD approved, pipeline starting", "assertive");
announce("Agent completed: Architecture", "polite");
announce("Error: Failed to approve", "assertive");
```

---

## 10. Offline & Degraded Mode

### 10.1 Connection States

| State | Indicator | Behavior |
|-------|-----------|----------|
| Connected | None (default) | Full functionality |
| Reconnecting | Yellow dot + "Reconnecting..." | Queue actions |
| Offline | Red banner | Show cached data |
| Degraded | Yellow banner | Partial functionality |

### 10.2 SSE Reconnection

```typescript
const sseConfig = {
  maxRetries: 10,
  initialDelay: 1000,
  maxDelay: 30000,
  backoffMultiplier: 2,
  onReconnect: () => refreshCurrentJob()
};
```

### 10.3 Cached Data

| Data | Cache Duration | Fallback |
|------|----------------|----------|
| Job list | 5 minutes | Show with "May be outdated" |
| PRD content | 30 minutes | Show cached version |
| Memory patterns | 1 hour | Show cached results |
| Metrics | 15 minutes | Show with timestamp |

---

## 11. Mobile Considerations

### 11.1 Responsive Behavior

| Breakpoint | Layout Changes |
|------------|----------------|
| < 640px | Single column, bottom nav, compact cards |
| 640-1024px | Two columns, sidebar collapses |
| > 1024px | Full layout, expanded sidebar |

### 11.2 Touch Interactions

| Gesture | Action |
|---------|--------|
| Tap | Select, navigate |
| Long press | Context menu |
| Pull to refresh | Refresh list/status |
| Swipe (card) | Quick actions |

### 11.3 Mobile Navigation

```
┌─────────────────────────────────────┐
│                                     │
│           (Page Content)            │
│                                     │
├─────────────────────────────────────┤
│  🏠      📁      ➕      🔍      📊  │
│ Home   Projects Create Memory Stats │
└─────────────────────────────────────┘
```

---

## 12. Implementation Phases

### Phase 1: Core MVP (Week 1-2)

**Goal**: Replace current minimal UI with functional React app

- [ ] Set up React + TypeScript + Vite + TailwindCSS
- [ ] Implement design tokens and base components
- [ ] Dashboard with project cards
- [ ] Create project form with validation
- [ ] Project status page with workflow progress
- [ ] PRD review page with approve/reject

### Phase 2: Memory Integration (Week 3)

**Goal**: Surface memory patterns throughout the UI

- [ ] Memory-assisted project creation (similar patterns)
- [ ] Memory hits sidebar on PRD review
- [ ] Memory explorer page
- [ ] Template reuse functionality

### Phase 3: Real-time & Polish (Week 4)

**Goal**: Real-time updates and production-ready polish

- [ ] SSE integration for live status updates
- [ ] Activity feed with live events
- [ ] All loading/empty/error states
- [ ] Toast notification system
- [ ] Confirmation dialogs

### Phase 4: Advanced Features (Week 5+)

**Goal**: Enhanced functionality and analytics

- [ ] Metrics dashboard
- [ ] Dark mode
- [ ] Keyboard shortcuts
- [ ] Mobile optimization
- [ ] Accessibility audit and fixes
- [ ] Offline support

---

## 13. Tech Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| Framework | React 18 | UI components |
| Language | TypeScript | Type safety |
| Styling | TailwindCSS | Utility-first CSS |
| State (Server) | TanStack Query | API data fetching/caching |
| State (Client) | Zustand | Local UI state |
| Routing | React Router v6 | Navigation |
| Real-time | EventSource (SSE) | Live updates |
| Icons | Lucide React | Icon library |
| Charts | Recharts | Data visualization |
| Build | Vite | Fast builds |
| Testing | Vitest + Testing Library | Unit/integration tests |

---

## 14. File Structure

```
web/
├── src/
│   ├── components/
│   │   ├── ui/                    # Base components
│   │   │   ├── Button.tsx
│   │   │   ├── Input.tsx
│   │   │   ├── Card.tsx
│   │   │   ├── Badge.tsx
│   │   │   ├── Modal.tsx
│   │   │   ├── Toast.tsx
│   │   │   └── Skeleton.tsx
│   │   ├── domain/                # Domain-specific
│   │   │   ├── WorkflowProgress.tsx
│   │   │   ├── AgentStatusCard.tsx
│   │   │   ├── MemoryHitCard.tsx
│   │   │   ├── ArtifactViewer.tsx
│   │   │   └── ActivityFeed.tsx
│   │   └── layout/
│   │       ├── Header.tsx
│   │       ├── Sidebar.tsx
│   │       └── PageLayout.tsx
│   ├── pages/
│   │   ├── Dashboard.tsx
│   │   ├── CreateProject.tsx
│   │   ├── ProjectStatus.tsx
│   │   ├── PRDReview.tsx
│   │   ├── Deliverables.tsx
│   │   ├── MemoryExplorer.tsx
│   │   └── Metrics.tsx
│   ├── hooks/
│   │   ├── useProject.ts
│   │   ├── useMemory.ts
│   │   ├── useEventStream.ts
│   │   └── useToast.ts
│   ├── api/
│   │   ├── client.ts
│   │   ├── projects.ts
│   │   ├── memory.ts
│   │   └── metrics.ts
│   ├── types/
│   │   └── index.ts
│   ├── styles/
│   │   └── tokens.css
│   ├── App.tsx
│   └── main.tsx
├── public/
├── package.json
├── vite.config.ts
├── tailwind.config.js
└── tsconfig.json
```

---

## 15. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Time to submit project | < 2 minutes | Analytics |
| PRD review completion | < 15 minutes | Time tracking |
| First-time user success | > 90% | Task completion |
| Memory pattern reuse | > 30% | Pattern usage stats |
| Mobile usability | > 4/5 rating | User feedback |
| Accessibility score | 100% Lighthouse | Automated audit |

---

## Appendix A: Agent to UI Mapping

| Agent | Stage | UI Element | Output Type |
|-------|-------|------------|-------------|
| prd_agent | PRD Generation | PRD Review Page | Markdown |
| plan_agent | Plan Generation | Plan Viewer | Markdown |
| architect_agent | Architecture | Architecture Viewer | Markdown |
| uiux_agent | UI/UX Design | Design System Viewer | JSON |
| developer_agent | Development | Development Plan Viewer | Markdown |
| qa_agent | QA Testing | QA Plan Viewer | Markdown |
| security_agent | Security Review | Security Report Viewer | Markdown |
| tech_writer | Documentation | Docs Viewer | Markdown |
| support_engineer | Support Docs | Support Guide Viewer | Markdown |
| product_manager | PM Review | Review Summary | Markdown |
| delivery_agent | Delivery | Download Package | ZIP |

---

## Appendix B: API Endpoints for UI

| UI Feature | Endpoint | Method |
|------------|----------|--------|
| Create project | `/api/projects/` | POST |
| Get job status | `/api/projects/{job_id}` | GET |
| Get PRD | `/api/projects/{job_id}/prd` | GET |
| Approve PRD | `/api/projects/{job_id}/approve` | POST |
| Request changes | `/api/projects/{job_id}/request_changes` | POST |
| Get artifacts | `/api/artifacts/job/{job_id}` | GET |
| Export ZIP | `/api/projects/{job_id}/export` | GET |
| Search memory | `/api/patterns/query` | POST |
| Get suggestions | `/api/patterns/suggest` | POST |
| Event stream | `/api/events/stream` | GET (SSE) |
| Metrics | `/api/metrics` | GET |
