# Agent Bus User Guide

Welcome to Agent Bus! This guide will help you get the most out of the system, whether you're submitting your first project or looking to optimize your workflow.

## Table of Contents

- [What is Agent Bus?](#what-is-agent-bus)
- [Getting Started](#getting-started)
- [Writing Effective Requirements](#writing-effective-requirements)
- [Understanding the Workflow](#understanding-the-workflow)
- [Reviewing and Approving (HITL)](#reviewing-and-approving-hitl)
- [Understanding Your Deliverables](#understanding-your-deliverables)
- [Tips for Best Results](#tips-for-best-results)
- [FAQ](#faq)
- [Troubleshooting](#troubleshooting)
- [Glossary](#glossary)

---

## What is Agent Bus?

Agent Bus is an AI-powered software engineering system that transforms your project requirements into comprehensive software deliverables. Instead of a single AI assistant, Agent Bus uses **12 specialized AI agents** that collaborate like a professional software team:

| Role | What They Do |
|------|--------------|
| **PRD Agent** | Writes detailed product requirements |
| **Plan Agent** | Creates project milestones and task breakdown |
| **Architect Agent** | Designs system architecture and tech stack |
| **UI/UX Agent** | Creates design systems and user interfaces |
| **Developer Agent** | Generates code with test-driven development |
| **QA Agent** | Creates test plans and quality strategies |
| **Security Agent** | Reviews for vulnerabilities and security issues |
| **Tech Writer** | Produces user documentation and guides |
| **Support Engineer** | Creates FAQ and troubleshooting docs |
| **Product Manager** | Reviews deliverables for completeness |
| **Memory Agent** | Learns from past projects to improve results |
| **Delivery Agent** | Packages everything for handoff |

### What You Get

When you submit a project, Agent Bus delivers:

- **Product Requirements Document (PRD)** - Detailed specification of what will be built
- **Project Plan** - Milestones, tasks, and dependencies
- **Architecture Design** - System design, database schemas, API specifications
- **UI/UX Design System** - Component library, style guide, mockups
- **Code Structure** - Implementation with tests
- **QA Test Plan** - Comprehensive testing strategy
- **Security Report** - Vulnerability assessment and recommendations
- **Documentation** - User guides and API documentation
- **Support Materials** - FAQ and troubleshooting guides

---

## Getting Started

### Step 1: Access Agent Bus

**Via API** (current method):
```bash
# Check that the system is running
curl http://localhost:8000/health
# Should return: {"status":"healthy"}
```

**Via Web UI**:
- Start the React frontend: `cd web && npm install && npm run dev`
- Navigate to `http://localhost:3000`
- Or use the legacy UI at `http://localhost:8000/ui/`

### Step 2: Submit Your Project

Send your requirements to start a new project:

```bash
curl -X POST http://localhost:8000/api/projects/ \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "my-first-project",
    "requirements": "Build a task management app where users can create projects, add tasks with due dates, and track progress with a dashboard."
  }'
```

You'll receive a **job ID** to track your project:
```json
{
  "job_id": "job_abc123",
  "status": "queued"
}
```

### Step 3: Monitor Progress

Check your project status anytime:

```bash
curl http://localhost:8000/api/projects/job_abc123
```

Or subscribe to real-time updates:
```bash
curl -N http://localhost:8000/api/events/stream
```

### Step 4: Review and Approve

When the PRD is ready, you'll need to review and approve it before development continues. See [Reviewing and Approving](#reviewing-and-approving-hitl) for details.

### Step 5: Receive Deliverables

Once complete, download your artifacts:
```bash
curl http://localhost:8000/api/projects/job_abc123/prd > prd.md
curl http://localhost:8000/api/projects/job_abc123/architecture > architecture.md
```

Or export all artifacts at once:
```bash
curl http://localhost:8000/api/projects/job_abc123/export -o artifacts.zip
```

### Using the CLI (Optional)

Agent Bus provides a CLI for common operations:

```bash
# List all jobs
agent-bus-jobs list

# Watch a job's progress in real-time
agent-bus-jobs watch job_abc123

# View job status
agent-bus-jobs status job_abc123

# Get artifacts
agent-bus-jobs result job_abc123

# Approve PRD
agent-bus-jobs approve job_abc123
```

---

## Writing Effective Requirements

The quality of your deliverables depends heavily on how well you describe your project. Here's how to write requirements that get great results.

### The Good Requirements Formula

**Good requirements answer these questions:**

1. **What** is being built? (type of application)
2. **Who** will use it? (target users)
3. **Why** do they need it? (problem being solved)
4. **What** features are essential? (core functionality)
5. **What** constraints exist? (scale, integrations, compliance)

### Examples

#### Too Vague (Poor Results)
```
"Build me a website"
```

#### Better
```
"Build an e-commerce website for selling handmade jewelry"
```

#### Best (Excellent Results)
```
"Build an e-commerce platform for a small business selling handmade jewelry.

Target users:
- Customers browsing and purchasing jewelry
- Shop owner managing inventory and orders

Core features:
- Product catalog with categories (necklaces, rings, earrings)
- Shopping cart and checkout with Stripe payments
- Customer accounts with order history
- Admin dashboard for inventory management
- Order notifications via email

Constraints:
- Must work on mobile devices
- Expect ~1000 monthly visitors initially
- Need to integrate with existing Instagram shop
```

### Requirements Checklist

Use this checklist to improve your requirements:

- [ ] **Application type** - Web app, mobile app, API, CLI tool?
- [ ] **Target users** - Who will use this? Different user roles?
- [ ] **Core features** - What are the must-have features?
- [ ] **User flows** - What actions do users need to perform?
- [ ] **Data** - What information needs to be stored?
- [ ] **Integrations** - Connect to other services? (payments, email, APIs)
- [ ] **Scale expectations** - How many users? How much data?
- [ ] **Platform requirements** - Browser support? Mobile? Desktop?
- [ ] **Security needs** - Authentication? Compliance requirements?
- [ ] **Non-functional requirements** - Performance? Availability?

### What NOT to Include

- Implementation details (let the Architect Agent decide)
- Specific technology choices (unless required)
- UI mockups (the UI/UX Agent will create these)
- Database schemas (the Architect Agent will design these)

Focus on **what** you need, not **how** to build it.

---

## Understanding the Workflow

Your project goes through 13 stages, each handled by a specialized agent:

```
┌─────────────────────────────────────────────────────────────────────┐
│                         YOUR PROJECT JOURNEY                         │
└─────────────────────────────────────────────────────────────────────┘

    ┌──────────┐     ┌──────────────────┐     ┌─────────────────┐
    │  START   │────▶│  PRD Generation  │────▶│  Your Approval  │
    │ (Submit) │     │    (2-5 min)     │     │   (HITL Gate)   │
    └──────────┘     └──────────────────┘     └────────┬────────┘
                                                       │
           ┌───────────────────────────────────────────┘
           │
           ▼
    ┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
    │ Plan Generation  │────▶│   Architecture   │────▶│   UI/UX Design   │
    │    (2-3 min)     │     │    (3-5 min)     │     │    (3-5 min)     │
    └──────────────────┘     └──────────────────┘     └────────┬─────────┘
                                                               │
           ┌───────────────────────────────────────────────────┘
           │
           ▼
    ┌──────────────────┐
    │   Development    │
    │    (5-8 min)     │
    └────────┬─────────┘
             │
             │  (These run in parallel)
             │
             ├────────────────┬────────────────┬────────────────┐
             ▼                ▼                ▼                ▼
    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
    │  QA Testing  │  │   Security   │  │Documentation │  │ Support Docs │
    │  (3-5 min)   │  │  (3-5 min)   │  │  (3-5 min)   │  │  (2-3 min)   │
    └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
           │                 │                 │                 │
           └────────────────┴────────────────┴────────────────┘
                                    │
                                    ▼
                          ┌──────────────────┐     ┌──────────────┐
                          │    PM Review     │────▶│   Delivery   │
                          │    (2-3 min)     │     │   Complete   │
                          └──────────────────┘     └──────────────┘
```

### Stage Details

| Stage | What Happens | What You'll See |
|-------|--------------|-----------------|
| **Queued** | Project received, waiting to start | Status: `queued` |
| **PRD Generation** | AI analyzes requirements, writes detailed PRD | Status: `prd_generation` |
| **Waiting Approval** | PRD ready for your review | Status: `waiting_approval` |
| **Plan Generation** | Creates milestones and task breakdown | Status: `plan_generation` |
| **Architecture** | Designs system, chooses technologies | Status: `architecture` |
| **UI/UX Design** | Creates design system and mockups | Status: `ui_ux_design` |
| **Development** | Generates code structure with tests | Status: `development` |
| **QA/Security/Docs** | Four agents work simultaneously | Status: various |
| **PM Review** | Final quality check | Status: `pm_review` |
| **Delivery** | Packages all artifacts | Status: `completed` |

### Timeline

**Typical project completion: 30-45 minutes**

This excludes the time you take to review and approve the PRD. The system waits for your approval before proceeding.

---

## Reviewing and Approving (HITL)

**HITL** stands for "Human-In-The-Loop" - points where the system pauses for your input.

### The PRD Approval Gate

After the PRD is generated, you must review and approve it before the project continues. This is your chance to:

- Verify the AI understood your requirements
- Add missing features or clarifications
- Correct any misunderstandings
- Reject and request changes

### How to Review

1. **Get the PRD**:
```bash
curl http://localhost:8000/api/projects/job_abc123/prd
```

2. **Read through and check**:
   - Are all your features included?
   - Is the scope correct?
   - Are there any assumptions you disagree with?
   - Is anything missing?

3. **Approve or Reject**:

**To approve:**
```bash
curl -X POST http://localhost:8000/api/projects/job_abc123/approve \
  -H "Content-Type: application/json" \
  -d '{"approved": true, "feedback": "Looks good, proceed!"}'
```

**To reject with feedback:**
```bash
curl -X POST http://localhost:8000/api/projects/job_abc123/approve \
  -H "Content-Type: application/json" \
  -d '{
    "approved": false,
    "feedback": "Please add user authentication with social login (Google, GitHub). Also, the analytics feature should include export to CSV."
  }'
```

### What Happens After Rejection?

The PRD Agent will revise the document based on your feedback, then present it for approval again. You can iterate until you're satisfied.

### Tips for Good Feedback

- Be specific about what's missing or wrong
- Reference specific sections if possible
- Provide examples when clarifying requirements
- Don't approve if you have concerns - it's harder to change later

---

## Understanding Your Deliverables

### Product Requirements Document (PRD)

**What it is:** A detailed specification of what will be built.

**What it contains:**
- Executive summary
- Problem statement
- User personas
- Feature specifications
- User stories
- Acceptance criteria
- Out-of-scope items

**How to use it:** Reference this document throughout development. It's the "source of truth" for what should be built.

### Project Plan

**What it is:** A breakdown of work into milestones and tasks.

**What it contains:**
- Milestones with deliverables
- Individual tasks with estimates
- Dependencies between tasks
- Priority ordering

**How to use it:** Track progress and understand the development sequence.

### Architecture Document

**What it is:** Technical design of the system.

**What it contains:**
- System overview diagram
- Component descriptions
- Database schema
- API specifications
- Technology choices with rationale
- Deployment architecture

**How to use it:** Hand to developers as the technical blueprint.

### UI/UX Design System

**What it is:** Visual and interaction design specifications.

**What it contains:**
- Design principles
- Color palette and typography
- Component library
- Page layouts/mockups
- Interaction patterns
- Responsive design guidelines

**How to use it:** Guide for frontend development and design consistency.

### Code Structure

**What it is:** Initial codebase with architecture implemented.

**What it contains:**
- Project structure
- Core modules and classes
- Database models
- API endpoints
- Test files
- Configuration

**How to use it:** Starting point for development team.

### QA Test Plan

**What it is:** Comprehensive testing strategy.

**What it contains:**
- Test strategy overview
- Test cases by feature
- Edge cases
- Performance test scenarios
- Security test scenarios

**How to use it:** Guide QA team's testing efforts.

### Security Report

**What it is:** Security assessment and recommendations.

**What it contains:**
- Threat model
- Vulnerability assessment
- Security recommendations
- Compliance considerations
- Security checklist

**How to use it:** Address security concerns before deployment.

### Documentation

**What it is:** User-facing documentation.

**What it contains:**
- User guide
- API documentation
- Setup instructions
- Feature documentation

**How to use it:** Provide to end users and developers.

### Support Materials

**What it is:** Support team resources.

**What it contains:**
- FAQ
- Troubleshooting guide
- Common issues and solutions
- Escalation procedures

**How to use it:** Enable support team to help users.

---

## Tips for Best Results

### Do

- **Be specific** - More detail leads to better results
- **Describe users** - Help the AI understand who will use the system
- **List must-have features** - Prioritize what's essential
- **Mention constraints** - Scale, budget, timeline, compliance
- **Provide context** - Business goals, existing systems, industry
- **Review carefully** - The PRD approval is your quality gate

### Don't

- **Don't be vague** - "Build something cool" won't work
- **Don't over-specify implementation** - Let the AI architect
- **Don't skip the PRD review** - Catch issues early
- **Don't rush approval** - Take time to verify understanding
- **Don't forget integrations** - Mention external services upfront

### Iteration Tips

If results aren't what you expected:

1. **Check your requirements** - Were they clear enough?
2. **Review the PRD** - Did you approve something incorrect?
3. **Submit again** - You can create a new project with refined requirements
4. **Use memory** - The system learns from patterns; similar future projects improve

---

## FAQ

### General Questions

**Q: How long does a project take?**

A: Typically 30-45 minutes of processing time, plus however long you take to review the PRD. Complex projects may take longer.

**Q: Can I submit multiple projects at once?**

A: Yes, each project runs independently with its own job ID.

**Q: What happens if I don't approve the PRD?**

A: The project stays in "waiting_approval" status until you approve or reject it. There's no timeout.

**Q: Can I cancel a project?**

A: You can delete a job using the API:
```bash
curl -X DELETE http://localhost:8000/api/projects/job_abc123
```

**Q: What happens if a job fails?**

A: Failed jobs can be restarted from the beginning:
```bash
curl -X POST http://localhost:8000/api/projects/job_abc123/restart
```
This clears all previous tasks and artifacts, then restarts from initialization.

**Q: What languages/frameworks does it support?**

A: The system is language-agnostic. Specify your preferred tech stack in requirements, or let the Architect Agent choose based on your project needs.

### Requirements Questions

**Q: How detailed should my requirements be?**

A: More detail is better. Include user types, features, constraints, and context. See [Writing Effective Requirements](#writing-effective-requirements).

**Q: Can I include mockups or diagrams?**

A: Currently, the system accepts text only. Describe visual requirements in words.

**Q: Should I specify the tech stack?**

A: Only if you have specific requirements (e.g., "must use Python" or "must integrate with our existing Node.js backend"). Otherwise, let the Architect Agent recommend.

### Deliverables Questions

**Q: Are the deliverables production-ready?**

A: Deliverables are high-quality starting points. They require human review and likely some customization before production deployment.

**Q: Can I request changes after completion?**

A: Submit a new project with updated requirements. The memory system helps the AI learn from previous projects.

**Q: What format are deliverables in?**

A: Primarily Markdown (.md) for documents, with code in appropriate languages. JSON for structured data like project plans.

### Technical Questions

**Q: Is my data secure?**

A: Data is stored in PostgreSQL with standard security practices. See your administrator for specific security policies.

**Q: What AI model powers this?**

A: Agent Bus uses Anthropic's Claude models. The specific model can be configured by administrators.

**Q: Can I self-host Agent Bus?**

A: Yes, Agent Bus is open-source. See the main README for deployment instructions.

---

## Troubleshooting

### Project Stuck in "Queued"

**Symptoms:** Project stays in `queued` status for more than 5 minutes.

**Causes:**
- Worker service not running
- Redis connection issues
- High system load

**Solutions:**
1. Check system health: `curl http://localhost:8000/health`
2. Contact administrator if health check fails
3. Wait if system is under heavy load

### PRD Not Generating

**Symptoms:** Project moves to `prd_generation` but doesn't complete.

**Causes:**
- LLM API issues
- Invalid API key
- Network problems

**Solutions:**
1. Check API status with your administrator
2. Try again in a few minutes
3. Check if other projects are completing successfully

### "Job Not Found" Error

**Symptoms:** Getting 404 when checking job status.

**Causes:**
- Incorrect job ID
- Job was deleted
- Database connection issues

**Solutions:**
1. Verify the job ID is correct
2. Contact administrator if job should exist

### Approval Not Working

**Symptoms:** Approval request returns error.

**Causes:**
- Project not in `waiting_approval` state
- Authentication issues
- Invalid request format

**Solutions:**
1. Check project status first
2. Ensure you're using correct JSON format
3. Verify authentication (if required)

### Deliverables Missing

**Symptoms:** Some expected artifacts not available.

**Causes:**
- Project not fully complete
- Specific agent failed
- Storage issues

**Solutions:**
1. Verify project status is `completed`
2. Check if specific stages failed
3. Contact administrator for failed stages

### Job Failed

**Symptoms:** Job status shows `failed`.

**Causes:**
- LLM API errors
- Timeout during processing
- Internal agent errors

**Solutions:**
1. Check job status for error details: `curl http://localhost:8000/api/projects/{job_id}`
2. Restart the job: `curl -X POST http://localhost:8000/api/projects/{job_id}/restart`
3. If the issue persists, check logs: `docker compose logs -f worker`

### Getting Help

If troubleshooting doesn't resolve your issue:

1. **Check logs** (administrators): `docker compose logs -f api`
2. **File an issue**: [GitHub Issues](https://github.com/tefj-fun/agent_bus/issues)
3. **Include details**: Job ID, error messages, steps to reproduce

---

## Glossary

| Term | Definition |
|------|------------|
| **Agent** | A specialized AI that handles one aspect of software development (e.g., PRD Agent, Architect Agent) |
| **Artifact** | A deliverable produced by an agent (e.g., PRD document, architecture design) |
| **HITL** | Human-In-The-Loop - points where human review/approval is required |
| **Job** | A project submission being processed by the system |
| **Job ID** | Unique identifier for tracking your project (e.g., `job_abc123`) |
| **Memory System** | AI memory that stores patterns from past projects to improve future results |
| **Orchestrator** | The component that coordinates all agents and manages workflow |
| **Pattern** | A reusable solution or template learned from previous projects |
| **PRD** | Product Requirements Document - detailed specification of what to build |
| **Stage** | A step in the workflow (e.g., `prd_generation`, `architecture`) |
| **Workflow** | The sequence of stages a project goes through from submission to delivery |
| **Worker** | Background process that executes agent tasks |

### Workflow Stages Reference

| Stage Code | Display Name | Description |
|------------|--------------|-------------|
| `queued` | Queued | Project received, waiting to start |
| `prd_generation` | PRD Generation | Creating product requirements |
| `waiting_approval` | Waiting Approval | PRD ready for human review |
| `plan_generation` | Plan Generation | Creating project plan |
| `architecture` | Architecture | Designing system architecture |
| `ui_ux_design` | UI/UX Design | Creating design system |
| `development` | Development | Generating code |
| `qa_testing` | QA Testing | Creating test plans |
| `security_review` | Security Review | Security assessment |
| `documentation` | Documentation | Writing user docs |
| `support_docs` | Support Docs | Creating support materials |
| `pm_review` | PM Review | Final quality check |
| `delivery` | Delivery | Packaging deliverables |
| `completed` | Completed | Project finished |
| `failed` | Failed | Project encountered error |

---

## Next Steps

Ready to start? Here's what to do:

1. **Write your requirements** using the [guidelines above](#writing-effective-requirements)
2. **Submit your project** via the API
3. **Monitor progress** with status checks or event stream
4. **Review and approve** the PRD carefully
5. **Download your deliverables** when complete

For technical documentation, see:
- [README.md](../README.md) - Technical overview and setup
- [Architecture](ARCHITECTURE.md) - System design details
- [API Documentation](http://localhost:8000/docs) - Swagger UI

---

*Have suggestions for this guide? [Open an issue](https://github.com/tefj-fun/agent_bus/issues) or submit a pull request.*
