# Externalization (Future Product) Notes

> Purpose: Keep a running checklist for turning agent_bus from an internal system into something other companies can use.
> This is **not** immediate scope; revisit after core pipeline + HITL are stable.

## What’s likely to be the product moat

1) **HITL governance**
- Approval gates between stages (PRD → Arch → Build → Release)
- Review UX: approve / request changes / regenerate / add constraints
- Audit trail: who approved what, when, and what changed

2) **Control room UX (single pane of glass)**
- Project stage timeline + current blockers
- Agent status (running/queued/failed) + logs
- Re-run / resume / rollback

3) **Artifacts-first, auditable outputs**
- PRD/Architecture/Plan as first-class artifacts
- Persistent storage + traceability (link artifacts ↔ tasks ↔ approvals)

4) **Safety + cost controls**
- Tool permissions, sandboxing, secret handling
- Rate limiting and budgets per org/project
- Redaction/PII policy hooks

## What is commoditized (not a differentiator)

- “Multi-agent orchestration” primitives by themselves
- Generic tool-calling wrappers
- Simple pipelines without governance + UI

## Externalization checklist (high level)

### Product/UX
- [ ] Role-based access control (RBAC): org/team/project roles
- [ ] Multi-tenancy boundaries (data isolation)
- [ ] Project templates + org standards
- [ ] Human approval workflows + notifications

### Integrations
- [ ] GitHub/GitLab (artifacts + PR workflows)
- [ ] Jira/Linear (tickets + status sync)
- [ ] Slack/Teams (alerts + approvals)

### Platform
- [ ] Hosted offering (SaaS)
- [ ] Self-host / on-prem deployment option
- [ ] Observability: metrics, tracing, structured logs
- [ ] Backups + retention + export

### Security/Compliance
- [ ] Secrets management (KMS/Vault)
- [ ] Audit log export
- [ ] PII handling + redaction controls
- [ ] Policy engine hooks

## Suggested packaging strategy

- **agent_bus (runtime)**: self-hostable core orchestration + artifact store
- **Control Room (UI + governance)**: paid product layer

## Notes / ideas

- Keep provider choice (OpenAI/Anthropic/etc.) as an implementation detail; maintain consistent artifacts/workflow.
- Optimize for “engineers can trust it” (auditability + reproducibility) rather than raw autonomy.
