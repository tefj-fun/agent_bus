import type { ReactNode } from 'react';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { parseArtifactJson } from './artifactParsing';
import { MarkdownRenderer } from './MarkdownRenderer';
import { JsonInspector } from './JsonInspector';

type ArchitecturePayload = {
  system_overview?: {
    description?: string;
    architecture_type?: string;
  };
  components?: Array<{
    id?: string;
    name?: string;
    type?: string;
    responsibilities?: string[];
    technology?: string;
    interfaces?: string[];
  }>;
  data_flows?: Array<{
    from?: string;
    to?: string;
    description?: string;
    protocol?: string;
  }>;
  data_models?: Array<{
    entity?: string;
    attributes?: string[];
    relationships?: string[];
  }>;
  technology_stack?: Record<string, string>;
  deployment?: Record<string, string>;
  security?: Record<string, string>;
  monitoring?: Record<string, string>;
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

export function ArchitectureRenderer({ content }: { content: string }) {
  const parsed = parseArtifactJson<ArchitecturePayload>(content, ['raw_architecture']);
  if (!parsed.data) {
    return <MarkdownRenderer content={parsed.raw || content} />;
  }

  const data = parsed.data;
  const components = Array.isArray(data.components) ? data.components : [];
  const flows = Array.isArray(data.data_flows) ? data.data_flows : [];
  const models = Array.isArray(data.data_models) ? data.data_models : [];

  const unknownKeys = Object.keys(data).filter(
    (key) =>
      ![
        'system_overview',
        'components',
        'data_flows',
        'data_models',
        'technology_stack',
        'deployment',
        'security',
        'monitoring',
      ].includes(key)
  );

  return (
    <div className="space-y-6">
      <div className="grid md:grid-cols-3 gap-4">
        <Card className="p-4">
          <p className="text-xs text-text-secondary">Components</p>
          <p className="text-2xl font-semibold text-text-primary">{components.length}</p>
        </Card>
        <Card className="p-4">
          <p className="text-xs text-text-secondary">Data Flows</p>
          <p className="text-2xl font-semibold text-text-primary">{flows.length}</p>
        </Card>
        <Card className="p-4">
          <p className="text-xs text-text-secondary">Data Models</p>
          <p className="text-2xl font-semibold text-text-primary">{models.length}</p>
        </Card>
      </div>

      {data.system_overview && (
        <Section title="System Overview">
          <Card className="p-4 space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <h4 className="text-sm font-semibold text-text-primary">Architecture</h4>
              {data.system_overview.architecture_type && (
                <Badge variant="info" size="sm">
                  {data.system_overview.architecture_type}
                </Badge>
              )}
            </div>
            {data.system_overview.description && (
              <p className="text-sm text-text-secondary">
                {data.system_overview.description}
              </p>
            )}
          </Card>
        </Section>
      )}

      {components.length > 0 && (
        <Section title="Components">
          <div className="space-y-3">
            {components.map((component) => (
              <Card key={component.id || component.name} className="p-4 space-y-2">
                <div className="flex flex-wrap items-center gap-2">
                  <h4 className="text-sm font-semibold text-text-primary">
                    {component.name || component.id || 'Component'}
                  </h4>
                  {component.type && (
                    <Badge variant="default" size="sm">
                      {component.type}
                    </Badge>
                  )}
                </div>
                {component.technology && (
                  <p className="text-xs text-text-secondary">
                    Technology: {component.technology}
                  </p>
                )}
                {Array.isArray(component.responsibilities) && component.responsibilities.length > 0 && (
                  <ul className="list-disc list-inside text-sm text-text-secondary space-y-1">
                    {component.responsibilities.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                )}
                {Array.isArray(component.interfaces) && component.interfaces.length > 0 && (
                  <div className="flex flex-wrap gap-2 text-xs">
                    {component.interfaces.map((item) => (
                      <Badge key={item} variant="info" size="sm">
                        {item}
                      </Badge>
                    ))}
                  </div>
                )}
              </Card>
            ))}
          </div>
        </Section>
      )}

      {flows.length > 0 && (
        <Section title="Data Flows">
          <div className="space-y-3">
            {flows.map((flow, index) => (
              <Card key={`${flow.from}-${flow.to}-${index}`} className="p-4 space-y-2">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant="default" size="sm">
                    {flow.from || 'source'}
                  </Badge>
                  <span className="text-text-muted text-xs">→</span>
                  <Badge variant="default" size="sm">
                    {flow.to || 'target'}
                  </Badge>
                  {flow.protocol && (
                    <Badge variant="info" size="sm">
                      {flow.protocol}
                    </Badge>
                  )}
                </div>
                {flow.description && (
                  <p className="text-sm text-text-secondary">{flow.description}</p>
                )}
              </Card>
            ))}
          </div>
        </Section>
      )}

      {models.length > 0 && (
        <Section title="Data Models">
          <div className="space-y-3">
            {models.map((model, index) => (
              <Card key={`${model.entity}-${index}`} className="p-4 space-y-2">
                <h4 className="text-sm font-semibold text-text-primary">
                  {model.entity || 'Entity'}
                </h4>
                {Array.isArray(model.attributes) && model.attributes.length > 0 && (
                  <div className="flex flex-wrap gap-2 text-xs">
                    {model.attributes.map((attr) => (
                      <Badge key={attr} variant="default" size="sm">
                        {attr}
                      </Badge>
                    ))}
                  </div>
                )}
                {Array.isArray(model.relationships) && model.relationships.length > 0 && (
                  <p className="text-sm text-text-secondary">
                    Relationships: {model.relationships.join(', ')}
                  </p>
                )}
              </Card>
            ))}
          </div>
        </Section>
      )}

      {data.technology_stack && (
        <Section title="Technology Stack">
          <Card className="p-4 space-y-2">
            {Object.entries(data.technology_stack).map(([key, value]) => (
              <div key={key} className="flex items-center justify-between text-sm">
                <span className="text-text-secondary">{key.replace(/_/g, ' ')}</span>
                <span className="text-text-primary font-medium">{value}</span>
              </div>
            ))}
          </Card>
        </Section>
      )}

      {data.deployment && (
        <Section title="Deployment">
          <Card className="p-4 space-y-2">
            {Object.entries(data.deployment).map(([key, value]) => (
              <div key={key} className="flex items-center justify-between text-sm">
                <span className="text-text-secondary">{key.replace(/_/g, ' ')}</span>
                <span className="text-text-primary font-medium">{value}</span>
              </div>
            ))}
          </Card>
        </Section>
      )}

      {data.security && (
        <Section title="Security">
          <Card className="p-4 space-y-2">
            {Object.entries(data.security).map(([key, value]) => (
              <div key={key} className="flex items-center justify-between text-sm">
                <span className="text-text-secondary">{key.replace(/_/g, ' ')}</span>
                <span className="text-text-primary font-medium">{value}</span>
              </div>
            ))}
          </Card>
        </Section>
      )}

      {data.monitoring && (
        <Section title="Monitoring">
          <Card className="p-4 space-y-2">
            {Object.entries(data.monitoring).map(([key, value]) => (
              <div key={key} className="flex items-center justify-between text-sm">
                <span className="text-text-secondary">{key.replace(/_/g, ' ')}</span>
                <span className="text-text-primary font-medium">{value}</span>
              </div>
            ))}
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
