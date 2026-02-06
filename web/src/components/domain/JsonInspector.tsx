import { Badge } from '../ui/Badge';

type JsonValue = string | number | boolean | null | JsonObject | JsonValue[];
type JsonObject = { [key: string]: JsonValue };

function isObject(value: JsonValue): value is JsonObject {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function formatPrimitive(value: JsonValue): string {
  if (value === null) return 'null';
  if (typeof value === 'boolean') return value ? 'true' : 'false';
  if (typeof value === 'number') return value.toString();
  return String(value);
}

function JsonNode({ value, depth }: { value: JsonValue; depth: number }) {
  if (Array.isArray(value)) {
    if (value.length === 0) {
      return <span className="text-text-muted text-sm">Empty list</span>;
    }
    return (
      <div className="space-y-2">
        {value.map((item, index) => (
          <div
            key={`${depth}-${index}`}
            className="pl-4 border-l border-border space-y-2"
          >
            <JsonNode value={item} depth={depth + 1} />
          </div>
        ))}
      </div>
    );
  }

  if (isObject(value)) {
    const entries = Object.entries(value);
    if (entries.length === 0) {
      return <span className="text-text-muted text-sm">Empty object</span>;
    }
    return (
      <div className="space-y-3">
        {entries.map(([key, child]) => (
          <div key={`${depth}-${key}`} className="space-y-2">
            <div className="text-xs font-semibold text-text-muted uppercase tracking-wide">
              {key.replace(/_/g, ' ')}
            </div>
            <div className="pl-4 border-l border-border">
              <JsonNode value={child} depth={depth + 1} />
            </div>
          </div>
        ))}
      </div>
    );
  }

  return (
    <Badge variant="default" size="sm">
      {formatPrimitive(value)}
    </Badge>
  );
}

export function JsonInspector({ data }: { data: JsonValue }) {
  return <JsonNode value={data} depth={0} />;
}
