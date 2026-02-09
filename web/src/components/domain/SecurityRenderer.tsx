import type { ReactNode } from 'react';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { parseArtifactJson } from './artifactParsing';
import { MarkdownRenderer } from './MarkdownRenderer';

type SecurityPayload = {
  security_audit?: Record<string, unknown>;
  vulnerabilities?: Array<{
    vulnerability_id?: string;
    severity?: string;
    category?: string;
    title?: string;
    description?: string;
    recommendation?: string;
    mitigation_priority?: string;
  }>;
  security_recommendations?: Array<{
    category?: string;
    priority?: string;
    recommendation?: string;
    rationale?: string;
    implementation_guidance?: string;
  }>;
  compliance_assessment?: Record<string, unknown>;
  security_best_practices?: Record<string, unknown>;
  penetration_testing?: Record<string, unknown>;
  security_metrics?: Record<string, unknown>;
  // Some producers emit rich objects here (e.g. { priority, action, owner, ... }).
  next_steps?: unknown[];
  [key: string]: unknown;
};

function toLabel(value: unknown): string {
  if (typeof value === 'string') return value;
  if (typeof value === 'number' || typeof value === 'boolean') return String(value);
  if (value && typeof value === 'object') {
    const obj = value as Record<string, unknown>;
    if (typeof obj.action === 'string' && obj.action.trim()) return obj.action;
    if (typeof obj.recommendation === 'string' && obj.recommendation.trim()) return obj.recommendation;
    if (typeof obj.title === 'string' && obj.title.trim()) return obj.title;
    if (typeof obj.name === 'string' && obj.name.trim()) return obj.name;
    if (typeof obj.id === 'string' && obj.id.trim()) return obj.id;
    return '[object]';
  }
  return '';
}

function toStableKey(value: unknown, fallback: string): string {
  if (typeof value === 'string' && value.trim()) return value;
  if (typeof value === 'number' || typeof value === 'boolean') return String(value);
  if (value && typeof value === 'object') {
    const obj = value as Record<string, unknown>;
    const parts: string[] = [];
    if (typeof obj.id === 'string' && obj.id.trim()) parts.push(obj.id);
    if (typeof obj.vulnerability_id === 'string' && obj.vulnerability_id.trim()) parts.push(obj.vulnerability_id);
    if (typeof obj.title === 'string' && obj.title.trim()) parts.push(obj.title);
    if (typeof obj.recommendation === 'string' && obj.recommendation.trim()) parts.push(obj.recommendation);
    if (typeof obj.action === 'string' && obj.action.trim()) parts.push(obj.action);
    if (typeof obj.owner === 'string' && obj.owner.trim()) parts.push(obj.owner);
    if (parts.length > 0) return parts.join(':');

    try {
      const json = JSON.stringify(value);
      if (json && json !== '{}') return json;
    } catch {
      // ignore
    }
  }
  return fallback;
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="space-y-3">
      <h3 className="text-base font-semibold text-text-primary">{title}</h3>
      {children}
    </section>
  );
}

function severityVariant(severity?: string) {
  const normalized = (severity || '').toLowerCase();
  if (['critical', 'high'].includes(normalized)) return 'error';
  if (['medium', 'moderate'].includes(normalized)) return 'warning';
  if (['low'].includes(normalized)) return 'info';
  return 'default';
}

function safeStringify(value: unknown, maxChars = 20000): string {
  try {
    const str = JSON.stringify(value, null, 2);
    if (str.length <= maxChars) return str;
    return `${str.slice(0, maxChars)}\n... (truncated; ${str.length} chars total)`;
  } catch {
    return String(value);
  }
}

function JsonSection({
  title,
  value,
  defaultOpen = false,
}: {
  title: string;
  value: unknown;
  defaultOpen?: boolean;
}) {
  return (
    <Section title={title}>
      <Card className="p-4">
        <details open={defaultOpen} className="rounded-md border border-border bg-bg-secondary p-3">
          <summary className="cursor-pointer text-sm font-semibold text-text-primary">
            View JSON
          </summary>
          <pre className="mt-3 whitespace-pre-wrap text-xs text-text-secondary overflow-auto max-h-[60vh]">
            {safeStringify(value)}
          </pre>
        </details>
      </Card>
    </Section>
  );
}

export function SecurityRenderer({ content }: { content: string }) {
  const parsed = parseArtifactJson<SecurityPayload>(content, ['raw_security']);
  if (!parsed.data) {
    return <MarkdownRenderer content={parsed.raw || content} />;
  }

  const data = parsed.data;
  const vulnerabilities = Array.isArray(data.vulnerabilities) ? data.vulnerabilities : [];
  const recommendations = Array.isArray(data.security_recommendations)
    ? data.security_recommendations
    : [];

  const unknownKeys = Object.keys(data).filter(
    (key) =>
      ![
        'security_audit',
        'vulnerabilities',
        'security_recommendations',
        'compliance_assessment',
        'security_best_practices',
        'penetration_testing',
        'security_metrics',
        'next_steps',
      ].includes(key)
  );

  return (
    <div className="space-y-6">
      <div className="grid md:grid-cols-3 gap-4">
        <Card className="p-4">
          <p className="text-xs text-text-secondary">Vulnerabilities</p>
          <p className="text-2xl font-semibold text-text-primary">
            {vulnerabilities.length}
          </p>
        </Card>
        <Card className="p-4">
          <p className="text-xs text-text-secondary">Recommendations</p>
          <p className="text-2xl font-semibold text-text-primary">
            {recommendations.length}
          </p>
        </Card>
        <Card className="p-4">
          <p className="text-xs text-text-secondary">Next Steps</p>
          <p className="text-2xl font-semibold text-text-primary">
            {Array.isArray(data.next_steps) ? data.next_steps.length : 0}
          </p>
        </Card>
      </div>

      {data.security_audit && (
        <JsonSection title="Security Audit Summary" value={data.security_audit} />
      )}

      {vulnerabilities.length > 0 && (
        <Section title="Vulnerabilities">
          <div className="space-y-3">
            {vulnerabilities.map((item, idx) => (
              <Card
                key={`${toStableKey(item.vulnerability_id || item.title, `vuln-${idx}`)}::${idx}`}
                className="p-4 space-y-2"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <h4 className="text-sm font-semibold text-text-primary">
                    {item.title || item.vulnerability_id || 'Vulnerability'}
                  </h4>
                  {item.severity && (
                    <Badge variant={severityVariant(item.severity)} size="sm">
                      {item.severity}
                    </Badge>
                  )}
                  {item.category && (
                    <Badge variant="info" size="sm">
                      {item.category}
                    </Badge>
                  )}
                </div>
                {item.description && (
                  <p className="text-sm text-text-secondary">{item.description}</p>
                )}
                {item.recommendation && (
                  <p className="text-sm text-text-secondary">
                    Recommendation: {item.recommendation}
                  </p>
                )}
                {item.mitigation_priority && (
                  <p className="text-xs text-text-secondary">
                    Mitigation priority: {item.mitigation_priority}
                  </p>
                )}
              </Card>
            ))}
          </div>
        </Section>
      )}

      {recommendations.length > 0 && (
        <Section title="Recommendations">
          <div className="space-y-3">
            {recommendations.map((rec, idx) => (
              <Card
                key={`${toStableKey(rec.recommendation || rec.category, `rec-${idx}`)}::${idx}`}
                className="p-4 space-y-2"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <h4 className="text-sm font-semibold text-text-primary">
                    {rec.recommendation || 'Recommendation'}
                  </h4>
                  {rec.priority && (
                    <Badge variant={severityVariant(rec.priority)} size="sm">
                      {rec.priority}
                    </Badge>
                  )}
                  {rec.category && (
                    <Badge variant="info" size="sm">
                      {rec.category}
                    </Badge>
                  )}
                </div>
                {rec.rationale && (
                  <p className="text-sm text-text-secondary">{rec.rationale}</p>
                )}
                {rec.implementation_guidance && (
                  <p className="text-sm text-text-secondary">
                    {rec.implementation_guidance}
                  </p>
                )}
              </Card>
            ))}
          </div>
        </Section>
      )}

      {data.compliance_assessment && (
        <JsonSection title="Compliance Assessment" value={data.compliance_assessment} />
      )}

      {data.security_best_practices && (
        <JsonSection title="Security Best Practices" value={data.security_best_practices} />
      )}

      {data.penetration_testing && (
        <JsonSection title="Penetration Testing" value={data.penetration_testing} />
      )}

      {data.security_metrics && (
        <JsonSection title="Security Metrics" value={data.security_metrics} />
      )}

      {Array.isArray(data.next_steps) && data.next_steps.length > 0 && (
        <Section title="Next Steps">
          <Card className="p-4">
            <ol className="list-decimal list-inside text-sm text-text-secondary space-y-1">
              {data.next_steps.map((step, idx) => {
                const key = `${toStableKey(step, `next-step-${idx}`)}::${idx}`;
                if (typeof step === 'string' || typeof step === 'number' || typeof step === 'boolean') {
                  return <li key={key}>{String(step)}</li>;
                }
                if (step && typeof step === 'object') {
                  const obj = step as Record<string, unknown>;
                  const action = toLabel(obj) || 'Next step';
                  const priority = typeof obj.priority === 'string' ? obj.priority : undefined;
                  const owner = typeof obj.owner === 'string' ? obj.owner : undefined;
                  const timeline = typeof obj.timeline === 'string' ? obj.timeline : undefined;
                  const dependencies = Array.isArray(obj.dependencies)
                    ? obj.dependencies.map((d) => toLabel(d) || '[object]').join(', ')
                    : typeof obj.dependencies === 'string'
                      ? obj.dependencies
                      : '';
                  const successCriteria = Array.isArray(obj.success_criteria)
                    ? obj.success_criteria.map((s) => toLabel(s) || '[object]').join(', ')
                    : typeof obj.success_criteria === 'string'
                      ? obj.success_criteria
                      : '';
                  return (
                    <li key={key}>
                      <div className="space-y-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="text-text-secondary">{action}</span>
                          {priority && (
                            <Badge variant={severityVariant(priority)} size="sm">
                              {priority}
                            </Badge>
                          )}
                          {owner && (
                            <Badge variant="default" size="sm">
                              {owner}
                            </Badge>
                          )}
                          {timeline && (
                            <Badge variant="info" size="sm">
                              {timeline}
                            </Badge>
                          )}
                        </div>
                        {dependencies && (
                          <div className="text-xs text-text-muted">Dependencies: {dependencies}</div>
                        )}
                        {successCriteria && (
                          <div className="text-xs text-text-muted">
                            Success criteria: {successCriteria}
                          </div>
                        )}
                      </div>
                    </li>
                  );
                }
                return <li key={key}>{toLabel(step) || 'Next step'}</li>;
              })}
            </ol>
          </Card>
        </Section>
      )}

      {unknownKeys.length > 0 && (
        <Section title="Additional Details">
          <Card className="p-4">
            <div className="space-y-3">
              <p className="text-sm text-text-secondary">
                These sections can be very large. Expand a section to view its raw JSON.
              </p>
              {unknownKeys.map((key) => (
                <details key={key} className="rounded-md border border-border bg-bg-secondary p-3">
                  <summary className="cursor-pointer text-sm font-semibold text-text-primary">
                    {key.replace(/_/g, ' ')}
                  </summary>
                  <pre className="mt-3 whitespace-pre-wrap text-xs text-text-secondary overflow-auto max-h-[60vh]">
                    {safeStringify(data[key])}
                  </pre>
                </details>
              ))}
            </div>
          </Card>
        </Section>
      )}
    </div>
  );
}
