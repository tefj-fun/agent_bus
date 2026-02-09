import { useMemo, useState } from 'react';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { Button } from '../ui/Button';

type PlanMilestone = {
  id?: string;
  name?: string;
  description?: string;
  tasks?: string[];
};

type PlanTask = {
  id?: string;
  title?: string;
  description?: string;
  owner?: string;
  dependencies?: string[];
};

type PlanRisk = string | { risk?: string; mitigation?: string };

type PlanPayload = {
  milestones?: PlanMilestone[];
  tasks?: PlanTask[];
  assumptions?: string[];
  risks?: PlanRisk[];
  raw_plan?: string;
};

type PlanRoot = PlanPayload & { plan?: unknown };

type ParseResult = {
  plan?: PlanPayload;
  raw?: string;
  error?: string;
};

function stripCodeFence(value: string): string {
  const trimmed = value.trim();
  const match = trimmed.match(/```(?:json)?\s*([\s\S]*?)```/i);
  return match ? match[1].trim() : trimmed;
}

function safeParse(value: string): { parsed?: PlanRoot; error?: string } {
  try {
    const parsed = JSON.parse(value) as PlanRoot;
    return { parsed };
  } catch (err) {
    return { error: err instanceof Error ? err.message : 'Invalid JSON' };
  }
}

function parsePlanContent(content: string): ParseResult {
  const trimmed = content.trim();
  let firstPass = safeParse(trimmed);
  if (!firstPass.parsed) {
    const cleaned = stripCodeFence(trimmed);
    firstPass = safeParse(cleaned);
  }
  if (!firstPass.parsed) {
    return { raw: content, error: firstPass.error || 'Invalid JSON' };
  }

  const payload = firstPass.parsed;
  if (payload.plan && typeof payload.plan === 'object') {
    return {
      plan: payload.plan as PlanPayload,
      raw: JSON.stringify(payload.plan, null, 2),
    };
  }
  if (payload.plan && typeof payload.plan === 'string') {
    const planText = payload.plan.trim();
    let planParsed = safeParse(planText);
    if (!planParsed.parsed) {
      const planCleaned = stripCodeFence(planText);
      planParsed = safeParse(planCleaned);
    }
    if (planParsed.parsed) {
      return {
        plan: planParsed.parsed,
        raw: JSON.stringify(planParsed.parsed, null, 2),
      };
    }
  }
  if (payload.raw_plan && typeof payload.raw_plan === 'string') {
    const rawText = payload.raw_plan.trim();
    let rawParsed = safeParse(rawText);
    if (!rawParsed.parsed) {
      const rawCleaned = stripCodeFence(rawText);
      rawParsed = safeParse(rawCleaned);
    }
    if (rawParsed.parsed) {
      return {
        plan: rawParsed.parsed,
        raw: JSON.stringify(rawParsed.parsed, null, 2),
      };
    }
    return {
      raw: payload.raw_plan,
      error: rawParsed.error || 'Unable to parse raw_plan',
    };
  }

  return {
    plan: payload,
    raw: JSON.stringify(payload, null, 2),
  };
}

function normalizeArray<T>(value: T[] | undefined): T[] {
  return Array.isArray(value) ? value : [];
}

export function PlanRenderer({ content }: { content: string }) {
  const [showRaw, setShowRaw] = useState(false);
  const parsed = useMemo(() => parsePlanContent(content), [content]);
  const plan = parsed.plan;

  const milestones = normalizeArray(plan?.milestones);
  const tasks = normalizeArray(plan?.tasks);
  const assumptions = normalizeArray(plan?.assumptions);
  const risks = normalizeArray(plan?.risks);

  const hasStructured =
    milestones.length > 0 || tasks.length > 0 || assumptions.length > 0 || risks.length > 0;

  const taskMap = useMemo(() => {
    return new Map(tasks.map((task) => [task.id || '', task]));
  }, [tasks]);

  const referencedTaskIds = new Set<string>();
  milestones.forEach((milestone) => {
    normalizeArray(milestone.tasks).forEach((taskId) => referencedTaskIds.add(taskId));
  });
  const unassignedTasks = tasks.filter((task) => task.id && !referencedTaskIds.has(task.id));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-text-primary">Project Plan</h2>
          <p className="text-sm text-text-secondary">
            Milestones, tasks, assumptions, and risks
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setShowRaw((prev) => !prev)}
        >
          {showRaw ? 'Hide Raw JSON' : 'View Raw JSON'}
        </Button>
      </div>

      {showRaw && (
        <Card variant="outlined" className="p-4">
          <pre className="doc-markdown whitespace-pre-wrap break-words">
            {parsed.raw || content}
          </pre>
        </Card>
      )}

      {!hasStructured && (
        <Card variant="outlined" className="p-4">
          <p className="text-text-secondary mb-2">
            Unable to render a structured plan.
          </p>
          <pre className="doc-markdown whitespace-pre-wrap break-words">
            {parsed.raw || content}
          </pre>
        </Card>
      )}

      {hasStructured && (
        <>
          <div className="grid md:grid-cols-4 gap-4">
            <Card className="p-4">
              <p className="text-xs text-text-secondary">Milestones</p>
              <p className="text-2xl font-semibold text-text-primary">{milestones.length}</p>
            </Card>
            <Card className="p-4">
              <p className="text-xs text-text-secondary">Tasks</p>
              <p className="text-2xl font-semibold text-text-primary">{tasks.length}</p>
            </Card>
            <Card className="p-4">
              <p className="text-xs text-text-secondary">Assumptions</p>
              <p className="text-2xl font-semibold text-text-primary">{assumptions.length}</p>
            </Card>
            <Card className="p-4">
              <p className="text-xs text-text-secondary">Risks</p>
              <p className="text-2xl font-semibold text-text-primary">{risks.length}</p>
            </Card>
          </div>

          {milestones.length > 0 && (
            <section className="space-y-4">
              <h3 className="text-base font-semibold text-text-primary">Milestones</h3>
              <div className="space-y-4">
                {milestones.map((milestone) => {
                  const milestoneTasks = normalizeArray(milestone.tasks).map((taskId) => {
                    const task = taskMap.get(taskId || '');
                    return task || { id: taskId, title: taskId };
                  });

                  return (
                    <Card key={milestone.id || milestone.name} className="p-4 space-y-3">
                      <div>
                        <div className="flex items-center gap-2">
                          <h4 className="font-semibold text-text-primary">
                            {milestone.name || milestone.id || 'Milestone'}
                          </h4>
                          {milestone.id && (
                            <Badge variant="default" size="sm">
                              {milestone.id}
                            </Badge>
                          )}
                        </div>
                        {milestone.description && (
                          <p className="text-sm text-text-secondary mt-1">
                            {milestone.description}
                          </p>
                        )}
                      </div>

                      {milestoneTasks.length > 0 && (
                        <div className="space-y-3">
                          <p className="text-xs text-text-muted uppercase tracking-wide">
                            Tasks
                          </p>
                          <div className="space-y-3">
                            {milestoneTasks.map((task) => (
                              <div
                                key={task.id || task.title}
                                className="p-3 rounded-lg border border-border bg-bg-secondary"
                              >
                                <div className="flex items-start justify-between gap-3">
                                  <div>
                                    <p className="font-medium text-text-primary">
                                      {task.title || task.id || 'Task'}
                                    </p>
                                    {task.id && (
                                      <p className="text-xs text-text-muted">{task.id}</p>
                                    )}
                                  </div>
                                  {task.owner && (
                                    <Badge variant="info" size="sm">
                                      {task.owner}
                                    </Badge>
                                  )}
                                </div>
                                {task.description && (
                                  <p className="text-sm text-text-secondary mt-2">
                                    {task.description}
                                  </p>
                                )}
                                {normalizeArray(task.dependencies).length > 0 && (
                                  <div className="flex flex-wrap items-center gap-2 mt-2 text-xs">
                                    <span className="text-text-muted">Dependencies:</span>
                                    {normalizeArray(task.dependencies).map((dep) => (
                                      <Badge key={dep} variant="default" size="sm">
                                        {dep}
                                      </Badge>
                                    ))}
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </Card>
                  );
                })}
              </div>
            </section>
          )}

          {unassignedTasks.length > 0 && (
            <section className="space-y-3">
              <h3 className="text-base font-semibold text-text-primary">Unassigned Tasks</h3>
              <Card className="p-4 space-y-3">
                {unassignedTasks.map((task) => (
                  <div key={task.id || task.title} className="border-b border-border pb-3 last:border-0 last:pb-0">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="font-medium text-text-primary">
                          {task.title || task.id || 'Task'}
                        </p>
                        {task.id && <p className="text-xs text-text-muted">{task.id}</p>}
                      </div>
                      {task.owner && (
                        <Badge variant="info" size="sm">
                          {task.owner}
                        </Badge>
                      )}
                    </div>
                    {task.description && (
                      <p className="text-sm text-text-secondary mt-2">{task.description}</p>
                    )}
                    {normalizeArray(task.dependencies).length > 0 && (
                      <div className="flex flex-wrap items-center gap-2 mt-2 text-xs">
                        <span className="text-text-muted">Dependencies:</span>
                        {normalizeArray(task.dependencies).map((dep) => (
                          <Badge key={dep} variant="default" size="sm">
                            {dep}
                          </Badge>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </Card>
            </section>
          )}

          {assumptions.length > 0 && (
            <section className="space-y-3">
              <h3 className="text-base font-semibold text-text-primary">Assumptions</h3>
              <Card className="p-4 space-y-2">
                {assumptions.map((assumption, index) => (
                  <div key={`${assumption}-${index}`} className="text-sm text-text-secondary">
                    - {assumption}
                  </div>
                ))}
              </Card>
            </section>
          )}

          {risks.length > 0 && (
            <section className="space-y-3">
              <h3 className="text-base font-semibold text-text-primary">Risks</h3>
              <Card className="p-4 space-y-3">
                {risks.map((risk, index) => {
                  const riskItem = typeof risk === 'string' ? { risk } : risk;
                  return (
                    <div key={`${riskItem.risk || 'risk'}-${index}`} className="space-y-1">
                      <p className="text-sm font-medium text-text-primary">
                        {riskItem.risk || 'Risk'}
                      </p>
                      {riskItem.mitigation && (
                        <p className="text-sm text-text-secondary">
                          Mitigation: {riskItem.mitigation}
                        </p>
                      )}
                    </div>
                  );
                })}
              </Card>
            </section>
          )}
        </>
      )}
    </div>
  );
}
