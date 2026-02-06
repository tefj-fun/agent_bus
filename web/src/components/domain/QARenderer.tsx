import type { ReactNode } from 'react';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { parseArtifactJson } from './artifactParsing';
import { MarkdownRenderer } from './MarkdownRenderer';
import { JsonInspector } from './JsonInspector';

type QAPayload = {
  qa_strategy?: Record<string, unknown>;
  test_plans?: Array<{
    plan_id?: string;
    name?: string;
    objective?: string;
    scope?: string;
    test_types?: string[];
    tools?: string[];
    coverage_target?: string;
    priority?: string;
  }>;
  test_cases?: Array<{
    case_id?: string;
    plan_id?: string;
    title?: string;
    description?: string;
    steps?: string[];
    expected_result?: string;
    priority?: string;
    test_type?: string;
  }>;
  coverage_strategy?: Record<string, unknown>;
  test_environment?: Record<string, unknown>;
  quality_metrics?: Record<string, unknown>;
  automation_strategy?: Record<string, unknown>;
  risk_assessment?: Array<Record<string, unknown>>;
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

export function QARenderer({ content }: { content: string }) {
  const parsed = parseArtifactJson<QAPayload>(content, ['raw_qa']);
  if (!parsed.data) {
    return <MarkdownRenderer content={parsed.raw || content} />;
  }

  const data = parsed.data;
  const plans = Array.isArray(data.test_plans) ? data.test_plans : [];
  const cases = Array.isArray(data.test_cases) ? data.test_cases : [];

  const unknownKeys = Object.keys(data).filter(
    (key) =>
      ![
        'qa_strategy',
        'test_plans',
        'test_cases',
        'coverage_strategy',
        'test_environment',
        'quality_metrics',
        'automation_strategy',
        'risk_assessment',
      ].includes(key)
  );

  return (
    <div className="space-y-6">
      <div className="grid md:grid-cols-3 gap-4">
        <Card className="p-4">
          <p className="text-xs text-text-secondary">Test Plans</p>
          <p className="text-2xl font-semibold text-text-primary">{plans.length}</p>
        </Card>
        <Card className="p-4">
          <p className="text-xs text-text-secondary">Test Cases</p>
          <p className="text-2xl font-semibold text-text-primary">{cases.length}</p>
        </Card>
        <Card className="p-4">
          <p className="text-xs text-text-secondary">Risk Items</p>
          <p className="text-2xl font-semibold text-text-primary">
            {Array.isArray(data.risk_assessment) ? data.risk_assessment.length : 0}
          </p>
        </Card>
      </div>

      {data.qa_strategy && (
        <Section title="QA Strategy">
          <Card className="p-4">
            <JsonInspector data={data.qa_strategy as Record<string, unknown>} />
          </Card>
        </Section>
      )}

      {plans.length > 0 && (
        <Section title="Test Plans">
          <div className="space-y-3">
            {plans.map((plan) => (
              <Card key={plan.plan_id || plan.name} className="p-4 space-y-2">
                <div className="flex flex-wrap items-center gap-2">
                  <h4 className="text-sm font-semibold text-text-primary">
                    {plan.name || plan.plan_id || 'Test Plan'}
                  </h4>
                  {plan.priority && (
                    <Badge variant="warning" size="sm">
                      {plan.priority}
                    </Badge>
                  )}
                </div>
                {plan.objective && (
                  <p className="text-sm text-text-secondary">{plan.objective}</p>
                )}
                {plan.scope && (
                  <p className="text-xs text-text-secondary">Scope: {plan.scope}</p>
                )}
                {plan.test_types && plan.test_types.length > 0 && (
                  <div className="flex flex-wrap gap-2 text-xs">
                    {plan.test_types.map((item) => (
                      <Badge key={item} variant="info" size="sm">
                        {item}
                      </Badge>
                    ))}
                  </div>
                )}
                {plan.tools && plan.tools.length > 0 && (
                  <p className="text-xs text-text-secondary">
                    Tools: {plan.tools.join(', ')}
                  </p>
                )}
                {plan.coverage_target && (
                  <p className="text-xs text-text-secondary">
                    Coverage target: {plan.coverage_target}
                  </p>
                )}
              </Card>
            ))}
          </div>
        </Section>
      )}

      {cases.length > 0 && (
        <Section title="Test Cases">
          <div className="space-y-3">
            {cases.map((testCase) => (
              <Card key={testCase.case_id || testCase.title} className="p-4 space-y-2">
                <div className="flex flex-wrap items-center gap-2">
                  <h4 className="text-sm font-semibold text-text-primary">
                    {testCase.title || testCase.case_id || 'Test Case'}
                  </h4>
                  {testCase.priority && (
                    <Badge variant="default" size="sm">
                      {testCase.priority}
                    </Badge>
                  )}
                </div>
                {testCase.description && (
                  <p className="text-sm text-text-secondary">{testCase.description}</p>
                )}
                {testCase.steps && testCase.steps.length > 0 && (
                  <ol className="list-decimal list-inside text-sm text-text-secondary space-y-1">
                    {testCase.steps.map((step) => (
                      <li key={step}>{step}</li>
                    ))}
                  </ol>
                )}
                {testCase.expected_result && (
                  <p className="text-xs text-text-secondary">
                    Expected: {testCase.expected_result}
                  </p>
                )}
                {testCase.test_type && (
                  <Badge variant="info" size="sm">
                    {testCase.test_type}
                  </Badge>
                )}
              </Card>
            ))}
          </div>
        </Section>
      )}

      {data.coverage_strategy && (
        <Section title="Coverage Strategy">
          <Card className="p-4">
            <JsonInspector data={data.coverage_strategy as Record<string, unknown>} />
          </Card>
        </Section>
      )}

      {data.test_environment && (
        <Section title="Test Environment">
          <Card className="p-4">
            <JsonInspector data={data.test_environment as Record<string, unknown>} />
          </Card>
        </Section>
      )}

      {data.quality_metrics && (
        <Section title="Quality Metrics">
          <Card className="p-4">
            <JsonInspector data={data.quality_metrics as Record<string, unknown>} />
          </Card>
        </Section>
      )}

      {data.automation_strategy && (
        <Section title="Automation Strategy">
          <Card className="p-4">
            <JsonInspector data={data.automation_strategy as Record<string, unknown>} />
          </Card>
        </Section>
      )}

      {Array.isArray(data.risk_assessment) && data.risk_assessment.length > 0 && (
        <Section title="Risk Assessment">
          <div className="space-y-3">
            {data.risk_assessment.map((risk, index) => (
              <Card key={String(risk.risk || index)} className="p-4 space-y-2">
                <p className="text-sm font-semibold text-text-primary">
                  {String(risk.risk || 'Risk')}
                </p>
                {risk.severity && (
                  <Badge variant="warning" size="sm">
                    {String(risk.severity)}
                  </Badge>
                )}
                {risk.mitigation && (
                  <p className="text-sm text-text-secondary">
                    Mitigation: {String(risk.mitigation)}
                  </p>
                )}
              </Card>
            ))}
          </div>
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
