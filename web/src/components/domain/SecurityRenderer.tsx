import type { ReactNode } from 'react';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { parseArtifactJson } from './artifactParsing';
import { MarkdownRenderer } from './MarkdownRenderer';
import { JsonInspector } from './JsonInspector';

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
  next_steps?: string[];
  [key: string]: unknown;
};

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
        <Section title="Security Audit Summary">
          <Card className="p-4">
            <JsonInspector data={data.security_audit as Record<string, unknown>} />
          </Card>
        </Section>
      )}

      {vulnerabilities.length > 0 && (
        <Section title="Vulnerabilities">
          <div className="space-y-3">
            {vulnerabilities.map((item) => (
              <Card key={item.vulnerability_id || item.title} className="p-4 space-y-2">
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
            {recommendations.map((rec) => (
              <Card key={rec.recommendation} className="p-4 space-y-2">
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
        <Section title="Compliance Assessment">
          <Card className="p-4">
            <JsonInspector data={data.compliance_assessment as Record<string, unknown>} />
          </Card>
        </Section>
      )}

      {data.security_best_practices && (
        <Section title="Security Best Practices">
          <Card className="p-4">
            <JsonInspector data={data.security_best_practices as Record<string, unknown>} />
          </Card>
        </Section>
      )}

      {data.penetration_testing && (
        <Section title="Penetration Testing">
          <Card className="p-4">
            <JsonInspector data={data.penetration_testing as Record<string, unknown>} />
          </Card>
        </Section>
      )}

      {data.security_metrics && (
        <Section title="Security Metrics">
          <Card className="p-4">
            <JsonInspector data={data.security_metrics as Record<string, unknown>} />
          </Card>
        </Section>
      )}

      {Array.isArray(data.next_steps) && data.next_steps.length > 0 && (
        <Section title="Next Steps">
          <Card className="p-4">
            <ol className="list-decimal list-inside text-sm text-text-secondary space-y-1">
              {data.next_steps.map((step) => (
                <li key={step}>{step}</li>
              ))}
            </ol>
          </Card>
        </Section>
      )}

      {unknownKeys.length > 0 && (
        <Section title="Additional Details">
          <Card className="p-4">
            <JsonInspector
              data={unknownKeys.reduce<Record<string, unknown>>((acc, key) => {
                acc[key] = data[key];
                return acc;
              }, {})}
            />
          </Card>
        </Section>
      )}
    </div>
  );
}
