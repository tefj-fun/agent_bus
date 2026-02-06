type ParseResult<T = unknown> = {
  data?: T;
  raw?: string;
  error?: string;
};

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
  return match ? match[1].trim() : trimmed;
}

export function parseArtifactJson<T = Record<string, unknown>>(
  content: string,
  rawKeys: string[] = []
): ParseResult<T> {
  const trimmed = content.trim();
  let parsed = safeParseJson<T>(trimmed);
  if (!parsed) {
    parsed = safeParseJson<T>(stripCodeFence(trimmed));
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

