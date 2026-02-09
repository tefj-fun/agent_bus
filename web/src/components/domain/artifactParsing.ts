type ParseResult<T = unknown> = {
  data?: T;
  raw?: string;
  error?: string;
};

function extractFirstJsonValue(text: string): string | undefined {
  // Extract the first balanced JSON value (object/array) from a larger text blob.
  // This is a best-effort helper for cases where agents wrap JSON in markdown or
  // include trailing commentary after the JSON.
  const startObj = text.indexOf('{');
  const startArr = text.indexOf('[');
  let start = -1;
  if (startObj === -1) start = startArr;
  else if (startArr === -1) start = startObj;
  else start = Math.min(startObj, startArr);

  if (start === -1) return undefined;

  let depth = 0;
  let inString = false;
  let escape = false;

  for (let i = start; i < text.length; i++) {
    const ch = text[i];

    if (inString) {
      if (escape) {
        escape = false;
        continue;
      }
      if (ch === '\\') {
        escape = true;
        continue;
      }
      if (ch === '"') {
        inString = false;
      }
      continue;
    }

    if (ch === '"') {
      inString = true;
      continue;
    }

    if (ch === '{' || ch === '[') {
      depth++;
      continue;
    }

    if (ch === '}' || ch === ']') {
      depth--;
      if (depth === 0) {
        return text.slice(start, i + 1).trim();
      }
    }
  }

  return undefined;
}

function safeParseJson<T = unknown>(value: string): T | undefined {
  try {
    return JSON.parse(value) as T;
  } catch {
    return undefined;
  }
}

export function stripCodeFence(value: string): string {
  const trimmed = value.trim();
  const match = trimmed.match(/```(?:json)?\s*([\s\S]*?)```/i);
  if (match) return match[1].trim();

  // Unclosed fence: take everything after the opening marker.
  const open = trimmed.match(/```(?:json)?\s*/i);
  if (open && typeof open.index === 'number') {
    return trimmed.slice(open.index + open[0].length).trim();
  }

  return trimmed;
}

export function parseArtifactJson<T = Record<string, unknown>>(
  content: string,
  rawKeys: string[] = []
): ParseResult<T> {
  const trimmed = content.trim();
  let parsed = safeParseJson<T>(trimmed);
  if (!parsed) {
    const unfenced = stripCodeFence(trimmed);
    parsed = safeParseJson<T>(unfenced);
    if (!parsed) {
      const extracted = extractFirstJsonValue(unfenced);
      if (extracted) parsed = safeParseJson<T>(extracted);
    }
  }

  if (!parsed) {
    return { raw: content, error: 'Invalid JSON' };
  }

  if (rawKeys.length && typeof parsed === 'object' && parsed) {
    for (const key of rawKeys) {
      const rawValue = (parsed as Record<string, unknown>)[key];
      if (typeof rawValue !== 'string') continue;

      const rawTrimmed = rawValue.trim();
      let rawParsed = safeParseJson<T>(rawTrimmed);
      if (!rawParsed) {
        rawParsed = safeParseJson<T>(stripCodeFence(rawTrimmed));
      }

      if (rawParsed) {
        return {
          data: rawParsed,
          raw: JSON.stringify(rawParsed, null, 2),
        };
      }

      return {
        raw: rawValue,
        error: `Unable to parse ${key}`,
      };
    }
  }

  return {
    data: parsed,
    raw: JSON.stringify(parsed, null, 2),
  };
}
