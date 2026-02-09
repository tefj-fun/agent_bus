import { Badge } from '../ui/Badge';

type JsonValue = string | number | boolean | null | JsonObject | JsonValue[];
type JsonObject = { [key: string]: JsonValue };

function isObject(value: JsonValue): value is JsonObject {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function coerceToJsonValue(
  value: unknown,
  depth = 0,
  seen: WeakSet<object> = new WeakSet()
): JsonValue {
  // Keep the inspector resilient: it should never crash on unexpected types.
  if (value === null) return null;

  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
    return value;
  }
  if (typeof value === 'undefined') return 'undefined';
  if (typeof value === 'bigint') return value.toString();
  if (typeof value === 'symbol') return value.toString();
  if (typeof value === 'function') return '[Function]';

  // Reasonable recursion limit to avoid freezing the UI on huge payloads.
  if (depth >= 8) return '[MaxDepth]';

  if (Array.isArray(value)) {
    return value.map((item) => coerceToJsonValue(item, depth + 1, seen));
  }

  if (value instanceof Date) return value.toISOString();

  if (value && typeof value === 'object') {
    const obj = value as object;
    if (seen.has(obj)) return '[Circular]';
    seen.add(obj);

    if (value instanceof Map) {
      return Array.from(value.entries()).map(([k, v]) => ({
        key: coerceToJsonValue(k, depth + 1, seen),
        value: coerceToJsonValue(v, depth + 1, seen),
      }));
    }

    if (value instanceof Set) {
      return Array.from(value.values()).map((v) => coerceToJsonValue(v, depth + 1, seen));
    }

    const out: JsonObject = {};
    for (const [k, v] of Object.entries(value as Record<string, unknown>)) {
      out[k] = coerceToJsonValue(v, depth + 1, seen);
    }
    return out;
  }

  // Should be unreachable, but keep it defensive.
  return String(value);
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

export function JsonInspector({ data }: { data: unknown }) {
  return <JsonNode value={coerceToJsonValue(data)} depth={0} />;
}
