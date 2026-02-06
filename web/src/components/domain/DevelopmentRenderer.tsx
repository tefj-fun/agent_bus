import type { ReactNode } from 'react';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { parseArtifactJson } from './artifactParsing';
import { MarkdownRenderer } from './MarkdownRenderer';
import { JsonInspector } from './JsonInspector';

type DevelopmentPayload = {
  tdd_strategy?: {
    approach?: string;
    test_framework?: string;
    coverage_target?: string;
    test_types?: string[];
  };
  development_phases?: Array<{
    phase?: number;
    name?: string;
    description?: string;
    tdd_steps?: string[];
  }>;
  code_structure?: Record<string, unknown>;
  testing_strategy?: Record<string, unknown>;
  quality_gates?: Record<string, unknown>;
  dependencies?: Record<string, string[]>;
  development_workflow?: Record<string, unknown>;
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

export function DevelopmentRenderer({ content }: { content: string }) {
  const parsed = parseArtifactJson<DevelopmentPayload>(content, ['raw_development']);
  if (!parsed.data) {
    return <MarkdownRenderer content={parsed.raw || content} />;
  }

  const data = parsed.data;
  const phases = Array.isArray(data.development_phases) ? data.development_phases : [];

  const unknownKeys = Object.keys(data).filter(
    (key) =>
      ![
        'tdd_strategy',
        'development_phases',
        'code_structure',
        'testing_strategy',
        'quality_gates',
        'dependencies',
        'development_workflow',
      ].includes(key)
  );

  return (
    <div className="space-y-6">
      {data.tdd_strategy && (
        <Section title="TDD Strategy">
          <Card className="p-4 space-y-2">
            {data.tdd_strategy.approach && (
              <p className="text-sm text-text-secondary">
                Approach: <span className="text-text-primary font-medium">{data.tdd_strategy.approach}</span>
              </p>
            )}
            {data.tdd_strategy.test_framework && (
              <p className="text-sm text-text-secondary">
                Framework: <span className="text-text-primary font-medium">{data.tdd_strategy.test_framework}</span>
              </p>
            )}
            {data.tdd_strategy.coverage_target && (
              <p className="text-sm text-text-secondary">
                Coverage target: <span className="text-text-primary font-medium">{data.tdd_strategy.coverage_target}</span>
              </p>
            )}
            {data.tdd_strategy.test_types && data.tdd_strategy.test_types.length > 0 && (
              <div className="flex flex-wrap gap-2 text-xs">
                {data.tdd_strategy.test_types.map((item) => (
                  <Badge key={item} variant="info" size="sm">
                    {item}
                  </Badge>
                ))}
              </div>
            )}
          </Card>
        </Section>
      )}

      {phases.length > 0 && (
        <Section title="Development Phases">
          <div className="space-y-3">
            {phases.map((phase) => (
              <Card key={phase.name || phase.phase} className="p-4 space-y-2">
                <div className="flex items-center gap-2">
                  {phase.phase !== undefined && (
                    <Badge variant="default" size="sm">
                      Phase {phase.phase}
                    </Badge>
                  )}
                  <h4 className="text-sm font-semibold text-text-primary">
                    {phase.name || 'Phase'}
                  </h4>
                </div>
                {phase.description && (
                  <p className="text-sm text-text-secondary">{phase.description}</p>
                )}
                {phase.tdd_steps && phase.tdd_steps.length > 0 && (
                  <ol className="list-decimal list-inside text-sm text-text-secondary space-y-1">
                    {phase.tdd_steps.map((step) => (
                      <li key={step}>{step}</li>
                    ))}
                  </ol>
                )}
              </Card>
            ))}
          </div>
        </Section>
      )}

      {data.code_structure && (
        <Section title="Code Structure">
          <Card className="p-4">
            <JsonInspector data={data.code_structure as Record<string, unknown>} />
          </Card>
        </Section>
      )}

      {data.testing_strategy && (
        <Section title="Testing Strategy">
          <Card className="p-4">
            <JsonInspector data={data.testing_strategy as Record<string, unknown>} />
          </Card>
        </Section>
      )}

      {data.quality_gates && (
        <Section title="Quality Gates">
          <Card className="p-4">
            <JsonInspector data={data.quality_gates as Record<string, unknown>} />
          </Card>
        </Section>
      )}

      {data.dependencies && (
        <Section title="Dependencies">
          <div className="grid md:grid-cols-2 gap-4">
            {Object.entries(data.dependencies).map(([key, deps]) => (
              <Card key={key} className="p-4 space-y-2">
                <h4 className="text-sm font-semibold text-text-primary capitalize">{key}</h4>
                {Array.isArray(deps) && deps.length > 0 ? (
                  <ul className="list-disc list-inside text-sm text-text-secondary space-y-1">
                    {deps.map((dep) => (
                      <li key={dep}>{dep}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-text-secondary">No dependencies listed</p>
                )}
              </Card>
            ))}
          </div>
        </Section>
      )}

      {data.development_workflow && (
        <Section title="Development Workflow">
          <Card className="p-4">
            <JsonInspector data={data.development_workflow as Record<string, unknown>} />
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
