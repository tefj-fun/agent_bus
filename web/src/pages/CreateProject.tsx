import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { PageLayout, PageHeader } from '../components/layout';
import { Card } from '../components/ui/Card';
import { Input } from '../components/ui/Input';
import { Textarea } from '../components/ui/Textarea';
import { Button } from '../components/ui/Button';
import { useToast } from '../components/ui/Toast';
import { MemoryHitCard } from '../components/domain/MemoryHitCard';
import { Skeleton } from '../components/ui/Skeleton';
import { useCreateProject } from '../hooks/useProject';
import { useDebouncedPatternSearch } from '../hooks/useMemory';
import { ArrowRight, Sparkles } from 'lucide-react';

export function CreateProject() {
  const navigate = useNavigate();
  const { addToast } = useToast();
  const createProject = useCreateProject();

  const [projectId, setProjectId] = useState('');
  const [requirements, setRequirements] = useState('');
  const [projectIdError, setProjectIdError] = useState<string | undefined>();
  const [requirementsError, setRequirementsError] = useState<string | undefined>();

  // Memory search as user types
  const { data: patterns, isLoading: searchingPatterns } = useDebouncedPatternSearch(requirements);

  const validateProjectId = (value: string): boolean => {
    if (!value) {
      setProjectIdError('Project ID is required');
      return false;
    }
    if (!/^[a-z0-9-]+$/.test(value)) {
      setProjectIdError('Use lowercase letters, numbers, and hyphens only');
      return false;
    }
    if (value.length < 3) {
      setProjectIdError('Must be at least 3 characters');
      return false;
    }
    setProjectIdError(undefined);
    return true;
  };

  const validateRequirements = (value: string): boolean => {
    if (!value) {
      setRequirementsError('Requirements are required');
      return false;
    }
    if (value.length < 100) {
      setRequirementsError(`Need at least 100 characters (${100 - value.length} more)`);
      return false;
    }
    setRequirementsError(undefined);
    return true;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const isValidId = validateProjectId(projectId);
    const isValidReqs = validateRequirements(requirements);

    if (!isValidId || !isValidReqs) return;

    try {
      const result = await createProject.mutateAsync({
        project_id: projectId,
        requirements,
      });

      addToast({
        type: 'success',
        title: 'Project Created',
        description: `Job ${result.job_id} has been queued`,
      });

      navigate(`/project/${result.job_id}`);
    } catch (err) {
      addToast({
        type: 'error',
        title: 'Failed to create project',
        description: err instanceof Error ? err.message : 'Unknown error',
      });
    }
  };

  const handleUsePattern = useCallback((text: string) => {
    // Append pattern context to requirements
    setRequirements(prev => {
      if (prev.includes(text.slice(0, 50))) return prev;
      return prev + '\n\nReference from similar project:\n' + text.slice(0, 500);
    });
    addToast({
      type: 'info',
      title: 'Pattern Applied',
      description: 'Reference added to your requirements',
    });
  }, [addToast]);

  return (
    <PageLayout>
      <PageHeader
        title="Create New Project"
        description="Transform customer requirements into comprehensive planning documents"
        backLink={{ href: '/', label: 'Back to Dashboard' }}
      />

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Main Form */}
        <div className="lg:col-span-2">
          <Card>
            <form onSubmit={handleSubmit} className="space-y-6">
              <Input
                label="Project ID"
                placeholder="e.g., payment-gateway-v2"
                value={projectId}
                onChange={(e) => {
                  setProjectId(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, '-'));
                  if (projectIdError) validateProjectId(e.target.value);
                }}
                onBlur={() => validateProjectId(projectId)}
                error={projectIdError}
                hint="Use lowercase letters, numbers, and hyphens"
                required
              />

              <Textarea
                label="Customer Requirements"
                placeholder={`Describe what the customer wants built...

Include:
- What the customer wants to build
- Key features and functionality
- Any technical constraints or preferences
- Timeline expectations`}
                value={requirements}
                onChange={(e) => {
                  setRequirements(e.target.value);
                  if (requirementsError) validateRequirements(e.target.value);
                }}
                onBlur={() => validateRequirements(requirements)}
                error={requirementsError}
                charCount={{
                  current: requirements.length,
                  min: 100,
                }}
                className="min-h-[250px]"
                required
              />

              <div className="flex items-center justify-between pt-4 border-t border-gray-200">
                <Button
                  type="button"
                  variant="ghost"
                  onClick={() => navigate('/')}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  loading={createProject.isPending}
                  icon={<ArrowRight className="w-4 h-4" />}
                >
                  Create Project
                </Button>
              </div>
            </form>
          </Card>
        </div>

        {/* Memory Suggestions Sidebar */}
        <div className="lg:col-span-1">
          <Card>
            <div className="flex items-center gap-2 mb-4">
              <Sparkles className="w-5 h-5 text-primary-500" />
              <h3 className="font-semibold text-gray-900">Similar Past Projects</h3>
            </div>

            {requirements.length < 50 ? (
              <p className="text-sm text-gray-500">
                Start typing requirements to see similar patterns from past projects...
              </p>
            ) : searchingPatterns ? (
              <div className="space-y-3">
                <Skeleton className="h-24 w-full rounded-lg" />
                <Skeleton className="h-24 w-full rounded-lg" />
              </div>
            ) : patterns?.patterns && patterns.patterns.length > 0 ? (
              <div className="space-y-3">
                {patterns.patterns.slice(0, 5).map((pattern) => (
                  <MemoryHitCard
                    key={pattern.id}
                    id={pattern.id}
                    title={pattern.metadata?.project_id as string || 'Past Project'}
                    patternType={pattern.metadata?.pattern_type as string || 'prd'}
                    similarity={pattern.score}
                    preview={pattern.text}
                    usageCount={pattern.metadata?.usage_count as number}
                    successRate={pattern.metadata?.success_rate as number}
                    onUseTemplate={() => handleUsePattern(pattern.text)}
                  />
                ))}
              </div>
            ) : (
              <div className="text-center py-6">
                <p className="text-sm text-gray-500">
                  No similar projects found.
                </p>
                <p className="text-xs text-gray-400 mt-1">
                  This will create new patterns in memory.
                </p>
              </div>
            )}
          </Card>
        </div>
      </div>
    </PageLayout>
  );
}
