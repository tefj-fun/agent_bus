# Agent Bus Web UI

Modern React-based web interface for Agent Bus - the multi-agent SWE planning system.

## Tech Stack

- **Framework**: React 18 + TypeScript
- **Build Tool**: Vite
- **Styling**: TailwindCSS with custom design tokens
- **State Management**: TanStack Query (React Query) + Zustand
- **Routing**: React Router v6
- **Icons**: Lucide React

## Quick Start

### Prerequisites

- Node.js 18+
- Agent Bus backend running on `http://localhost:8000`

### Development

```bash
# Install dependencies
npm install

# Start development server
npm run dev
```

Access the app at http://localhost:3000/

### Production Build

```bash
# Build for production
npm run build

# Preview production build
npm run preview
```

## Project Structure

```
web/
├── src/
│   ├── api/
│   │   └── client.ts          # Typed API client
│   ├── components/
│   │   ├── ui/                # Base UI components
│   │   │   ├── Button.tsx
│   │   │   ├── Card.tsx
│   │   │   ├── Badge.tsx
│   │   │   ├── Input.tsx
│   │   │   ├── Textarea.tsx
│   │   │   ├── Modal.tsx
│   │   │   ├── Toast.tsx
│   │   │   └── Skeleton.tsx
│   │   ├── domain/            # Domain-specific components
│   │   │   ├── WorkflowProgress.tsx
│   │   │   ├── MemoryHitCard.tsx
│   │   │   ├── ActivityFeed.tsx
│   │   │   └── ArtifactViewer.tsx
│   │   └── layout/            # Layout components
│   │       ├── Header.tsx
│   │       └── PageLayout.tsx
│   ├── hooks/
│   │   ├── useProject.ts      # Project/job queries
│   │   ├── useMemory.ts       # Memory/pattern queries
│   │   └── useEventStream.ts  # SSE connection
│   ├── pages/
│   │   ├── Dashboard.tsx      # Home - stats & project list
│   │   ├── CreateProject.tsx  # New project form
│   │   ├── PRDReview.tsx      # HITL approval gate
│   │   ├── ProjectStatus.tsx  # Workflow progress
│   │   └── Deliverables.tsx   # Artifact downloads
│   ├── styles/
│   │   └── tokens.css         # TailwindCSS design tokens
│   ├── types/
│   │   └── index.ts           # TypeScript definitions
│   ├── utils/
│   │   └── utils.ts           # Utility functions
│   ├── App.tsx                # Router setup
│   └── main.tsx               # Entry point
├── package.json
├── vite.config.ts
└── tsconfig.json
```

## Pages & Routes

| Route | Page | Description |
|-------|------|-------------|
| `/` | Dashboard | Overview stats, pending reviews, active/completed projects |
| `/new` | CreateProject | Form with memory-assisted suggestions |
| `/project/:jobId` | ProjectStatus | Workflow progress with real-time SSE updates |
| `/prd/:jobId` | PRDReview | View PRD, approve/request changes (HITL gate) |
| `/project/:jobId/deliverables` | Deliverables | Download individual or all artifacts |

## Features

### Dashboard
- Project statistics (total, pending review, in progress, completed)
- Pending reviews requiring attention
- Active and completed project lists
- Quick actions to create new projects

### Project Creation
- Requirements input with rich textarea
- Memory-assisted suggestions based on past patterns
- Template suggestions from similar projects

### PRD Review (HITL Gate)
- Full PRD document display
- Approve or Request Changes actions
- Notes/feedback field for change requests

### Workflow Progress
- Visual pipeline with 10 stages
- Real-time status updates via SSE
- Activity feed showing agent events
- Stage completion indicators

### Deliverables
- List of all generated artifacts
- Individual artifact viewing
- Download individual files
- Download all as ZIP

## Configuration

The app proxies API requests to the backend. Configure in `vite.config.ts`:

```typescript
server: {
  port: 3000,
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
    },
  },
},
```

## Design System

See [UIUX_PLAN.md](../docs/UIUX_PLAN.md) for the complete design specification including:
- Color palette and design tokens
- Typography scale
- Component specifications
- Page layouts and wireframes
- Accessibility guidelines
