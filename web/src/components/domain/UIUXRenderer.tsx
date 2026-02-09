import type { ReactNode } from 'react';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { parseArtifactJson } from './artifactParsing';
import { MarkdownRenderer } from './MarkdownRenderer';
import { JsonInspector } from './JsonInspector';

type UIUXPayload = {
  design_system?: {
    name?: string;
    version?: string;
    description?: string;
  };
  color_palette?: Record<string, string | Record<string, string>>;
  typography?: Record<string, unknown>;
  spacing?: Record<string, unknown>;
  breakpoints?: Record<string, unknown>;
  components?: Array<{
    name?: string;
    description?: string;
    // Some producers emit rich objects here (e.g. { name, appearance, use_case }).
    variants?: unknown[];
    states?: unknown[];
    props?: unknown[];
  }>;
  layouts?: Array<{
    name?: string;
    structure?: string;
    use_cases?: unknown[];
    breakpoints?: unknown[];
  }>;
  user_flows?: Array<{
    name?: string;
    steps?: unknown[];
    screens?: unknown[];
    interactions?: unknown[];
  }>;
  accessibility?: Record<string, unknown>;
  animations?: Record<string, unknown>;
  [key: string]: unknown;
};

function toLabel(value: unknown): string {
  if (typeof value === 'string') return value;
  if (typeof value === 'number' || typeof value === 'boolean') return String(value);
  if (value && typeof value === 'object') {
    const obj = value as Record<string, unknown>;
    if (typeof obj.name === 'string' && obj.name.trim()) return obj.name;
    if (typeof obj.label === 'string' && obj.label.trim()) return obj.label;
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
    if (typeof obj.name === 'string' && obj.name.trim()) parts.push(obj.name);
    if (typeof obj.appearance === 'string' && obj.appearance.trim()) parts.push(obj.appearance);
    if (typeof obj.use_case === 'string' && obj.use_case.trim()) parts.push(obj.use_case);
    if (parts.length > 0) return parts.join(':');

    // Last resort: stable-ish string for keys without crashing render.
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

function ColorSwatch({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3 text-sm">
      <span className="text-text-secondary">{label}</span>
      <div className="flex items-center gap-2">
        <span className="text-xs text-text-muted">{value}</span>
        <span
          className="h-4 w-4 rounded-full border border-border"
          style={{ backgroundColor: value || 'var(--color-border)' }}
        />
      </div>
    </div>
  );
}

export function UIUXRenderer({ content }: { content: string }) {
  const parsed = parseArtifactJson<UIUXPayload>(content, ['raw_design']);
  if (!parsed.data) {
    return <MarkdownRenderer content={parsed.raw || content} />;
  }

  const data = parsed.data;
  const components = Array.isArray(data.components) ? data.components : [];
  const layouts = Array.isArray(data.layouts) ? data.layouts : [];
  const flows = Array.isArray(data.user_flows) ? data.user_flows : [];

  const unknownKeys = Object.keys(data).filter(
    (key) =>
      ![
        'design_system',
        'color_palette',
        'typography',
        'spacing',
        'breakpoints',
        'components',
        'layouts',
        'user_flows',
        'accessibility',
        'animations',
      ].includes(key)
  );

  return (
    <div className="space-y-6">
      {data.design_system && (
        <Card className="p-4 space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-lg font-semibold text-text-primary">
              {data.design_system.name || 'Design System'}
            </h2>
            {data.design_system.version && (
              <Badge variant="info" size="sm">
                v{data.design_system.version}
              </Badge>
            )}
          </div>
          {data.design_system.description && (
            <p className="text-sm text-text-secondary">
              {data.design_system.description}
            </p>
          )}
        </Card>
      )}

      {data.color_palette && (
        <Section title="Color Palette">
          <Card className="p-4 space-y-3">
            {Object.entries(data.color_palette).map(([key, value]) => {
              if (typeof value === 'string') {
                return <ColorSwatch key={key} label={key} value={value} />;
              }
              if (value && typeof value === 'object') {
                return (
                  <div key={key} className="space-y-2">
                    <p className="text-xs font-semibold text-text-muted uppercase tracking-wide">
                      {key}
                    </p>
                    <div className="space-y-2 pl-4 border-l border-border">
                      {Object.entries(value).map(([subKey, subValue]) => (
                        <ColorSwatch
                          key={`${key}-${subKey}`}
                          label={subKey}
                          value={String(subValue)}
                        />
                      ))}
                    </div>
                  </div>
                );
              }
              return null;
            })}
          </Card>
        </Section>
      )}

      {data.typography && (
        <Section title="Typography">
          <Card className="p-4">
            <JsonInspector data={data.typography as unknown as Record<string, unknown>} />
          </Card>
        </Section>
      )}

      {(data.spacing || data.breakpoints) && (
        <Section title="Spacing & Breakpoints">
          <Card className="p-4 space-y-4">
            {data.spacing && (
              <div>
                <p className="text-xs font-semibold text-text-muted uppercase tracking-wide">
                  Spacing
                </p>
                <div className="mt-2">
                  <JsonInspector data={data.spacing as unknown as Record<string, unknown>} />
                </div>
              </div>
            )}
            {data.breakpoints && (
              <div>
                <p className="text-xs font-semibold text-text-muted uppercase tracking-wide">
                  Breakpoints
                </p>
                <div className="mt-2">
                  <JsonInspector
                    data={data.breakpoints as unknown as Record<string, unknown>}
                  />
                </div>
              </div>
            )}
          </Card>
        </Section>
      )}

      {components.length > 0 && (
        <Section title="Components">
          <div className="space-y-3">
            {components.map((component, componentIdx) => (
              <Card
                key={toStableKey(component.name, `component-${componentIdx}`)}
                className="p-4 space-y-2"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <h4 className="text-sm font-semibold text-text-primary">
                    {component.name || 'Component'}
                  </h4>
                  {Array.isArray(component.variants) && component.variants.length > 0 && (
                    <Badge variant="default" size="sm">
                      {component.variants.length} variants
                    </Badge>
                  )}
                </div>
                {component.description && (
                  <p className="text-sm text-text-secondary">{component.description}</p>
                )}
                {Array.isArray(component.variants) && component.variants.length > 0 && (
                  <div className="flex flex-wrap gap-2 text-xs">
                    {component.variants.map((variant, variantIdx) => {
                      const label = toLabel(variant) || 'Variant';
                      const keyBase = toStableKey(
                        variant,
                        `variant-${component.name || componentIdx}-${variantIdx}`
                      );
                      const key = `${keyBase}::${variantIdx}`;
                      return (
                        <Badge key={key} variant="info" size="sm">
                          {label}
                        </Badge>
                      );
                    })}
                  </div>
                )}
                {Array.isArray(component.states) && component.states.length > 0 && (
                  <p className="text-xs text-text-secondary">
                    States: {component.states.map((s) => toLabel(s) || '[object]').join(', ')}
                  </p>
                )}
                {Array.isArray(component.props) && component.props.length > 0 && (
                  <p className="text-xs text-text-secondary">
                    Props: {component.props.map((p) => toLabel(p) || '[object]').join(', ')}
                  </p>
                )}
              </Card>
            ))}
          </div>
        </Section>
      )}

      {layouts.length > 0 && (
        <Section title="Layouts">
          <div className="space-y-3">
            {layouts.map((layout, layoutIdx) => (
              <Card key={toStableKey(layout.name, `layout-${layoutIdx}`)} className="p-4 space-y-2">
                <h4 className="text-sm font-semibold text-text-primary">
                  {layout.name || 'Layout'}
                </h4>
                {layout.structure && (
                  <p className="text-sm text-text-secondary">{layout.structure}</p>
                )}
                {Array.isArray(layout.use_cases) && layout.use_cases.length > 0 && (
                  <p className="text-xs text-text-secondary">
                    Use cases: {layout.use_cases.map((u) => toLabel(u) || '[object]').join(', ')}
                  </p>
                )}
                {Array.isArray(layout.breakpoints) && layout.breakpoints.length > 0 && (
                  <div className="flex flex-wrap gap-2 text-xs">
                    {layout.breakpoints.map((bp, bpIdx) => {
                      const label = toLabel(bp) || 'Breakpoint';
                      const keyBase = toStableKey(bp, `bp-${layout.name || layoutIdx}-${bpIdx}`);
                      const key = `${keyBase}::${bpIdx}`;
                      return (
                        <Badge key={key} variant="default" size="sm">
                          {label}
                        </Badge>
                      );
                    })}
                  </div>
                )}
              </Card>
            ))}
          </div>
        </Section>
      )}

      {flows.length > 0 && (
        <Section title="User Flows">
          <div className="space-y-3">
            {flows.map((flow, flowIdx) => (
              <Card key={toStableKey(flow.name, `flow-${flowIdx}`)} className="p-4 space-y-2">
                <h4 className="text-sm font-semibold text-text-primary">
                  {flow.name || 'Flow'}
                </h4>
                {Array.isArray(flow.steps) && flow.steps.length > 0 && (
                  <ol className="list-decimal list-inside text-sm text-text-secondary space-y-1">
                    {flow.steps.map((step, stepIdx) => {
                      const label = toLabel(step) || 'Step';
                      const keyBase = toStableKey(step, `step-${flow.name || flowIdx}-${stepIdx}`);
                      const key = `${keyBase}::${stepIdx}`;
                      return <li key={key}>{label}</li>;
                    })}
                  </ol>
                )}
                {Array.isArray(flow.screens) && flow.screens.length > 0 && (
                  <p className="text-xs text-text-secondary">
                    Screens: {flow.screens.map((s) => toLabel(s) || '[object]').join(', ')}
                  </p>
                )}
                {Array.isArray(flow.interactions) && flow.interactions.length > 0 && (
                  <div className="flex flex-wrap gap-2 text-xs">
                    {flow.interactions.map((item, itemIdx) => {
                      const label = toLabel(item) || 'Interaction';
                      const keyBase = toStableKey(
                        item,
                        `interaction-${flow.name || flowIdx}-${itemIdx}`
                      );
                      const key = `${keyBase}::${itemIdx}`;
                      return (
                        <Badge key={key} variant="info" size="sm">
                          {label}
                        </Badge>
                      );
                    })}
                  </div>
                )}
              </Card>
            ))}
          </div>
        </Section>
      )}

      {data.accessibility && (
        <Section title="Accessibility">
          <Card className="p-4">
            <JsonInspector data={data.accessibility as unknown as Record<string, unknown>} />
          </Card>
        </Section>
      )}

      {data.animations && (
        <Section title="Motion & Animations">
          <Card className="p-4">
            <JsonInspector data={data.animations as unknown as Record<string, unknown>} />
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
