# Agent Notes (Codex)

This file describes how I (the Codex agent) should operate in this repo, with a light
reference to the existing Claude guidance.

## Relationship To Claude Guidance
- `CLAUDE.md` is the primary collaboration guide for this project.
- When this file and `CLAUDE.md` conflict, follow `CLAUDE.md` unless the user explicitly
  overrides it for a specific task.

## Operating Principles
- Prefer small, reviewable edits.
- Favor explicit, low-risk changes over clever ones.
- Ask before making large refactors or behavior changes.
- If something is ambiguous, ask a focused question rather than guessing.

## Tooling And Execution
- Use the local repo tools and scripts when available.
- Surface command outputs concisely in responses.
- Do not run destructive commands unless explicitly requested.

## Communication
- State assumptions and tradeoffs clearly.
- Provide file references when describing changes.
- Suggest next steps only when there is a natural follow-on action.
