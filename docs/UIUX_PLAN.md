# Agent Bus UI/UX Design Plan

## Overview
Modern React-based web application for managing AI-powered software projects from requirements to delivery.

## Design Principles
1. **Clarity First**: Make complex AI workflows understandable at a glance
2. **Progressive Disclosure**: Show essential info first, details on demand
3. **Real-time Feedback**: Live updates as agents work
4. **Trust Through Transparency**: Show what agents are doing and why
5. **Mobile Responsive**: Works on desktop, tablet, mobile

## Tech Stack
- **Framework**: React 18 + TypeScript
- **Styling**: TailwindCSS + Headless UI
- **State**: React Query (server state) + Zustand (client state)
- **Real-time**: Server-Sent Events (SSE)
- **Icons**: Heroicons
- **Charts**: Recharts (for metrics)
- **Build**: Vite

## User Flows

### Primary Flow: Create Project
```
Landing → Requirements Form → Job Created → 
  → PRD Review → Approve/Reject → 
    → Live Progress Dashboard → 
      → View Deliverables → Download All
```

### Secondary Flows
- Browse past projects
- Search memory for patterns
- View system metrics
- Manage settings

## Page Structure

### 1. Dashboard (Home)
**Route**: `/`

**Layout**:
```
┌─────────────────────────────────────────┐
│  [Logo] Agent Bus    [User] [Settings]  │
├─────────────────────────────────────────┤
│                                          │
│  ┌────────────────────────────────────┐ │
│  │  Create New Project                │ │
│  │  + New Project                     │ │
│  └────────────────────────────────────┘ │
│                                          │
│  Active Projects (3)                    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐│
│  │ Proj A   │ │ Proj B   │ │ Proj C   ││
│  │ In Prog  │ │ Waiting  │ │ Complete ││
│  │ 45%      │ │ PRD      │ │ ✓        ││
│  └──────────┘ └──────────┘ └──────────┘│
│                                          │
│  Recent Projects                        │
│  • Todo App - Completed 2h ago          │
│  • SaaS Dashboard - Completed 1d ago    │
│  • API Gateway - Completed 3d ago       │
│                                          │
└─────────────────────────────────────────┘
```

**Features**:
- Quick "New Project" button (prominent)
- Active projects as cards with progress
- Recent projects list
- Stats: Total projects, Success rate, Avg time

### 2. Requirements Form
**Route**: `/new`

**Layout**:
```
┌─────────────────────────────────────────┐
│  ← Back to Dashboard                    │
├─────────────────────────────────────────┤
│                                          │
│  Create New Project                     │
│                                          │
│  Project ID                             │
│  [___________________________________] │
│  e.g. "saas-analytics-dashboard"        │
│                                          │
│  Requirements                           │
│  ┌─────────────────────────────────────┐│
│  │                                     ││
│  │  Describe what you want built...   ││
│  │                                     ││
│  │                                     ││
│  └─────────────────────────────────────┘│
│  500+ characters recommended            │
│                                          │
│  💡 Suggestions from Memory:            │
│  • SaaS web app template                │
│  • Analytics dashboard pattern          │
│  • Authentication boilerplate           │
│                                          │
│  [Cancel]              [Create Project] │
│                                          │
└─────────────────────────────────────────┘
```

**Features**:
- Auto-save to localStorage
- Character count
- Template suggestions from memory
- Validation feedback
- Loading state on submit

### 3. Project Detail / Live Progress
**Route**: `/project/:jobId`

**Layout**:
```
┌─────────────────────────────────────────┐
│  ← Projects    Calculator App           │
├─────────────────────────────────────────┤
│  Status: In Progress • Started 5m ago   │
│                                          │
│  Workflow Progress                      │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│  ✓ PRD → ✓ Plan → ⚡ Architecture → ... │
│                                          │
│  Current Stage: Architecture Design     │
│  ┌─────────────────────────────────────┐│
│  │ 🏗️ Architect Agent                  ││
│  │ Designing system architecture...    ││
│  │ ⏱️ 2m 15s elapsed                   ││
│  │ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ││
│  └─────────────────────────────────────┘│
│                                          │
│  Completed Stages                       │
│  ✓ PRD Generation (3m 20s)              │
│  ✓ Plan Generation (2m 45s)             │
│                                          │
│  Live Activity Feed                     │
│  • 14:23 - Architecture stage started   │
│  • 14:20 - Plan approved                │
│  • 14:18 - PRD completed                │
│                                          │
│  [View PRD] [View Plan]                 │
│                                          │
└─────────────────────────────────────────┘
```

**Features**:
- Real-time updates via SSE
- Visual workflow progress bar
- Current stage highlighted with animation
- Time elapsed per stage
- Activity feed (last 20 events)
- Links to view completed artifacts
- Auto-refresh every 2s as fallback

### 4. PRD Review & Approval
**Route**: `/project/:jobId/prd`

**Layout**:
```
┌─────────────────────────────────────────┐
│  ← Back to Project                      │
├─────────────────────────────────────────┤
│  Product Requirements Document          │
│  Calculator App                         │
│                                          │
│  [Overview] [Functional] [Technical]    │
│  [Timeline] [Success Criteria]          │
│                                          │
│  ┌─────────────────────────────────────┐│
│  │ ## Overview                         ││
│  │                                     ││
│  │ Build a calculator web application ││
│  │ with Chinese font numbers...       ││
│  │                                     ││
│  │ ## Core Features                   ││
│  │ 1. Basic arithmetic operations     ││
│  │ 2. Chinese numeral display         ││
│  │ ...                                ││
│  └─────────────────────────────────────┘│
│                                          │
│  💡 Similar Projects:                   │
│  • Math Tools Suite (95% match)         │
│  • Scientific Calculator (87% match)    │
│                                          │
│  Feedback (optional)                    │
│  [_________________________________]   │
│                                          │
│  [❌ Request Changes]     [✓ Approve]   │
│                                          │
└─────────────────────────────────────────┘
```

**Features**:
- Markdown rendering with syntax highlighting
- Tabbed sections for easy navigation
- Memory matches sidebar
- Inline comments (future)
- Download as PDF/Markdown
- Approve/Reject with optional feedback

### 5. Artifacts & Deliverables
**Route**: `/project/:jobId/deliverables`

**Layout**:
```
┌─────────────────────────────────────────┐
│  ← Back to Project                      │
├─────────────────────────────────────────┤
│  Project Deliverables                   │
│  Calculator App • Completed 45m ago     │
│                                          │
│  [Download All as ZIP]                  │
│                                          │
│  Documents                              │
│  ┌──────────────────────────────────┐  │
│  │ 📄 Product Requirements Document │  │
│  │    Generated 40m ago • 2.3 KB   │  │
│  │    [View] [Download]             │  │
│  └──────────────────────────────────┘  │
│  ┌──────────────────────────────────┐  │
│  │ 🏗️ System Architecture          │  │
│  │    Generated 35m ago • 4.1 KB   │  │
│  │    [View] [Download]             │  │
│  └──────────────────────────────────┘  │
│  ┌──────────────────────────────────┐  │
│  │ 📋 Project Plan                  │  │
│  │    Generated 38m ago • 3.5 KB   │  │
│  │    [View] [Download]             │  │
│  └──────────────────────────────────┘  │
│                                          │
│  Code & Implementation                  │
│  ┌──────────────────────────────────┐  │
│  │ 💻 Development Plan              │  │
│  │    Generated 30m ago • 5.2 KB   │  │
│  │    [View] [Download]             │  │
│  └──────────────────────────────────┘  │
│                                          │
│  Quality & Security                     │
│  ┌──────────────────────────────────┐  │
│  │ ✅ QA Test Plan                  │  │
│  │ 🔒 Security Review               │  │
│  │ 📚 Documentation                 │  │
│  │ 🎧 Support Guide                 │  │
│  └──────────────────────────────────┘  │
│                                          │
└─────────────────────────────────────────┘
```

**Features**:
- Grouped by category
- File size and timestamp
- Preview and download
- Bulk download as ZIP
- Copy to clipboard

### 6. Memory Explorer
**Route**: `/memory`

**Layout**:
```
┌─────────────────────────────────────────┐
│  Agent Bus • Memory                     │
├─────────────────────────────────────────┤
│                                          │
│  Search Patterns                        │
│  [🔍 _____________________________]    │
│  Search across all past projects...     │
│                                          │
│  [PRD] [Architecture] [Code] [All]      │
│                                          │
│  Results (127 patterns)                 │
│  ┌──────────────────────────────────┐  │
│  │ 📄 SaaS Dashboard PRD            │  │
│  │    95% match • Used 12 times    │  │
│  │    "Multi-tenant dashboard..."  │  │
│  │    [View] [Use as Template]     │  │
│  └──────────────────────────────────┘  │
│  ┌──────────────────────────────────┐  │
│  │ 🏗️ Microservices Architecture   │  │
│  │    87% match • Used 8 times     │  │
│  │    "Event-driven architecture..."│  │
│  │    [View] [Use as Template]     │  │
│  └──────────────────────────────────┘  │
│                                          │
│  Popular Templates                      │
│  • Web App Boilerplate (45 uses)        │
│  • REST API Pattern (38 uses)           │
│  • React Dashboard (31 uses)            │
│                                          │
└─────────────────────────────────────────┘
```

**Features**:
- Full-text search
- Filter by pattern type
- Similarity scoring
- Usage statistics
- Template application

### 7. System Metrics
**Route**: `/metrics`

**Layout**:
```
┌─────────────────────────────────────────┐
│  Agent Bus • Metrics                    │
├─────────────────────────────────────────┤
│                                          │
│  Overview (Last 7 days)                 │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐  │
│  │   156   │ │   98%   │ │ 32m     │  │
│  │Projects │ │Success  │ │Avg Time │  │
│  └─────────┘ └─────────┘ └─────────┘  │
│                                          │
│  Projects Over Time                     │
│  ┌─────────────────────────────────────┐│
│  │     📊 Line Chart                   ││
│  │  20 ┤                            ╭─╮││
│  │  15 ┤                      ╭─────╯ │││
│  │  10 ┤            ╭─────────╯       │││
│  │   5 ┤    ╭───────╯                 │││
│  │   0 ┼────┴──────────────────────────││
│  │     Mon Tue Wed Thu Fri Sat Sun    ││
│  └─────────────────────────────────────┘│
│                                          │
│  Agent Performance                      │
│  • PRD Agent: 3.2m avg, 99% success     │
│  • Architect: 4.1m avg, 98% success     │
│  • Developer: 7.5m avg, 97% success     │
│  • QA Agent: 3.8m avg, 99% success      │
│                                          │
│  Resource Usage                         │
│  • LLM Tokens: 2.4M used this week      │
│  • Memory Queries: 1,847                │
│  • GPU Jobs: 23 (15% of total)          │
│                                          │
└─────────────────────────────────────────┘
```

**Features**:
- Key metrics at a glance
- Interactive charts
- Agent performance breakdown
- Resource usage tracking
- Export data as CSV

## Components Library

### Core Components
1. **ProjectCard** - Displays project summary
2. **ProgressBar** - Visual workflow progress
3. **StageIndicator** - Current stage with animation
4. **ArtifactViewer** - Markdown/code viewer
5. **ActivityFeed** - Real-time event stream
6. **PatternCard** - Memory search result
7. **MetricsChart** - Data visualization
8. **ApprovalModal** - PRD review interface

### Design Tokens

**Colors**:
```css
--primary: #2563eb (blue)
--success: #10b981 (green)
--warning: #f59e0b (amber)
--error: #ef4444 (red)
--bg: #ffffff (white)
--bg-secondary: #f9fafb (gray-50)
--text: #111827 (gray-900)
--text-secondary: #6b7280 (gray-500)
--border: #e5e7eb (gray-200)
```

**Typography**:
- Headings: Inter (font-semibold)
- Body: Inter (font-normal)
- Code: JetBrains Mono

**Spacing**: 4px base (Tailwind default)

**Borders**: Rounded (8px cards, 6px buttons)

## Responsive Breakpoints
- Mobile: 640px
- Tablet: 768px
- Desktop: 1024px
- Large: 1280px

## Animations
- **Page transitions**: Fade in (200ms)
- **Stage progress**: Pulse animation on active stage
- **Activity feed**: Slide in from right
- **Loading states**: Skeleton screens

## Accessibility
- WCAG 2.1 Level AA compliance
- Keyboard navigation
- Screen reader support
- High contrast mode
- Focus indicators
- ARIA labels

## Implementation Phases

### Phase 1: MVP (Week 1)
- Dashboard (home)
- Requirements form
- Project detail with live progress
- Basic PRD viewer

### Phase 2: Core Features (Week 2)
- PRD approval flow
- Artifacts/deliverables page
- Activity feed with SSE
- Download functionality

### Phase 3: Polish (Week 3)
- Memory explorer
- System metrics
- Responsive design
- Error states

### Phase 4: Advanced (Week 4)
- User authentication UI
- Settings page
- Dark mode
- Advanced filters

## File Structure
```
web/
├── src/
│   ├── components/
│   │   ├── ProjectCard.tsx
│   │   ├── ProgressBar.tsx
│   │   ├── StageIndicator.tsx
│   │   ├── ArtifactViewer.tsx
│   │   ├── ActivityFeed.tsx
│   │   └── ...
│   ├── pages/
│   │   ├── Dashboard.tsx
│   │   ├── NewProject.tsx
│   │   ├── ProjectDetail.tsx
│   │   ├── PRDReview.tsx
│   │   ├── Deliverables.tsx
│   │   ├── Memory.tsx
│   │   └── Metrics.tsx
│   ├── hooks/
│   │   ├── useProject.ts
│   │   ├── useEventStream.ts
│   │   └── useMemory.ts
│   ├── api/
│   │   └── client.ts
│   ├── types/
│   │   └── index.ts
│   ├── App.tsx
│   └── main.tsx
├── public/
├── package.json
├── vite.config.ts
└── tailwind.config.js
```

## Success Metrics
- Time to first project: <2 minutes
- PRD approval rate: >85%
- User satisfaction: >4.5/5
- Mobile usage: >20%
- Return user rate: >60%
