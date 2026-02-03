import { useState } from 'react';
import { PageLayout, PageHeader } from '../components/layout';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Search, Database, FileText, Code, Shield, BookOpen, Layers } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface PatternResult {
  id: string;
  text: string;
  score: number;
  metadata: {
    pattern_type?: string;
    success_score?: string;
    usage_count?: string;
  };
}

interface QueryResponse {
  status: string;
  query: string;
  results: PatternResult[];
  count: number;
}

interface PatternTypesResponse {
  status: string;
  total_patterns: number;
  common_types: string[];
}

const PATTERN_ICONS: Record<string, React.ReactNode> = {
  prd: <FileText className="w-4 h-4" />,
  architecture: <Layers className="w-4 h-4" />,
  code: <Code className="w-4 h-4" />,
  test: <Shield className="w-4 h-4" />,
  documentation: <BookOpen className="w-4 h-4" />,
  template: <Database className="w-4 h-4" />,
  general: <Database className="w-4 h-4" />,
};

export function Memory() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<PatternResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [patternType, setPatternType] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState<PatternTypesResponse | null>(null);

  const loadStats = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/patterns/types`);
      if (res.ok) {
        const data = await res.json();
        setStats(data);
      }
    } catch {
      // Ignore stats errors
    }
  };

  const handleSearch = async () => {
    if (!query.trim()) return;

    setIsSearching(true);
    setError(null);

    try {
      const res = await fetch(`${API_BASE}/api/patterns/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: query.trim(),
          top_k: 10,
          pattern_type: patternType,
        }),
      });

      if (!res.ok) {
        throw new Error(`Search failed: ${res.status}`);
      }

      const data: QueryResponse = await res.json();
      setResults(data.results);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Search failed');
      setResults([]);
    } finally {
      setIsSearching(false);
    }
  };

  // Load stats on mount
  useState(() => {
    loadStats();
  });

  return (
    <PageLayout>
      <PageHeader
        title="Memory Store"
        description="Search and explore patterns stored in the memory system"
      />

      {/* Stats */}
      {stats && (
        <Card className="mb-6">
          <div className="flex items-center gap-4">
            <Database className="w-6 h-6 text-primary-500" />
            <div>
              <p className="text-lg font-semibold text-gray-900">
                {stats.total_patterns} patterns
              </p>
              <p className="text-sm text-gray-500">stored in memory</p>
            </div>
          </div>
        </Card>
      )}

      {/* Search */}
      <Card className="mb-6">
        <div className="space-y-4">
          <div className="flex gap-2">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              placeholder="Search patterns..."
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            />
            <Button
              onClick={handleSearch}
              disabled={isSearching || !query.trim()}
              icon={<Search className="w-4 h-4" />}
            >
              {isSearching ? 'Searching...' : 'Search'}
            </Button>
          </div>

          {/* Pattern type filter */}
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => setPatternType(null)}
              className={`px-3 py-1 rounded-full text-sm transition-colors ${
                patternType === null
                  ? 'bg-primary-100 text-primary-700'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              All Types
            </button>
            {(stats?.common_types || ['prd', 'architecture', 'code', 'test', 'documentation', 'template']).map((type) => (
              <button
                key={type}
                onClick={() => setPatternType(type)}
                className={`px-3 py-1 rounded-full text-sm flex items-center gap-1 transition-colors ${
                  patternType === type
                    ? 'bg-primary-100 text-primary-700'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {PATTERN_ICONS[type] || <Database className="w-3 h-3" />}
                {type}
              </button>
            ))}
          </div>
        </div>
      </Card>

      {/* Error */}
      {error && (
        <Card variant="outlined" className="mb-6 border-error-200 bg-error-50">
          <p className="text-error-700">{error}</p>
        </Card>
      )}

      {/* Results */}
      {results.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-lg font-semibold text-gray-900">
            {results.length} result{results.length !== 1 ? 's' : ''}
          </h2>
          {results.map((result) => (
            <Card key={result.id} variant="outlined">
              <div className="flex items-start justify-between mb-2">
                <div className="flex items-center gap-2">
                  {PATTERN_ICONS[result.metadata.pattern_type || 'general']}
                  <Badge variant="default">
                    {result.metadata.pattern_type || 'general'}
                  </Badge>
                  <span className="text-sm text-gray-500">
                    Score: {(result.score * 100).toFixed(1)}%
                  </span>
                </div>
                <span className="text-xs text-gray-400 font-mono">{result.id}</span>
              </div>
              <p className="text-gray-700 whitespace-pre-wrap text-sm">
                {result.text.length > 500
                  ? `${result.text.slice(0, 500)}...`
                  : result.text}
              </p>
              {result.metadata.usage_count && (
                <p className="text-xs text-gray-400 mt-2">
                  Used {result.metadata.usage_count} time{result.metadata.usage_count !== '1' ? 's' : ''}
                </p>
              )}
            </Card>
          ))}
        </div>
      )}

      {/* Empty state */}
      {results.length === 0 && !error && !isSearching && (
        <Card variant="outlined" className="text-center py-12">
          <Search className="w-12 h-12 text-gray-300 mx-auto mb-4" />
          <p className="text-gray-500 mb-2">Search for patterns in memory</p>
          <p className="text-sm text-gray-400">
            Enter a query to find similar patterns, templates, and solutions
          </p>
        </Card>
      )}
    </PageLayout>
  );
}
