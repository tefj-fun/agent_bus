-- Database initialization script for agent_bus

-- Jobs table - tracks overall project jobs
CREATE TABLE IF NOT EXISTS jobs (
    id VARCHAR(255) PRIMARY KEY,
    project_id VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL,
    workflow_stage VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_jobs_project_id ON jobs(project_id);
CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_jobs_created_at ON jobs(created_at);

-- Tasks table - individual agent tasks within a job
CREATE TABLE IF NOT EXISTS tasks (
    id VARCHAR(255) PRIMARY KEY,
    job_id VARCHAR(255) NOT NULL REFERENCES jobs(id),
    agent_id VARCHAR(100) NOT NULL,
    task_type VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL,
    priority INTEGER DEFAULT 5,
    input_data JSONB DEFAULT '{}'::jsonb,
    output_data JSONB DEFAULT '{}'::jsonb,
    dependencies TEXT[] DEFAULT ARRAY[]::TEXT[],
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error TEXT,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_tasks_job_id ON tasks(job_id);
CREATE INDEX idx_tasks_agent_id ON tasks(agent_id);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_created_at ON tasks(created_at);

-- Artifacts table - outputs created by agents
CREATE TABLE IF NOT EXISTS artifacts (
    id VARCHAR(255) PRIMARY KEY,
    agent_id VARCHAR(100) NOT NULL,
    job_id VARCHAR(255) NOT NULL REFERENCES jobs(id),
    type VARCHAR(100) NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_artifacts_job_id ON artifacts(job_id);
CREATE INDEX idx_artifacts_agent_id ON artifacts(agent_id);
CREATE INDEX idx_artifacts_type ON artifacts(type);

-- Agent events table - logging agent activities
CREATE TABLE IF NOT EXISTS agent_events (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(100) NOT NULL,
    job_id VARCHAR(255) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    message TEXT NOT NULL,
    data JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_events_job_id ON agent_events(job_id);
CREATE INDEX idx_events_agent_id ON agent_events(agent_id);
CREATE INDEX idx_events_type ON agent_events(event_type);
CREATE INDEX idx_events_created_at ON agent_events(created_at);

-- Memory patterns table - for the memory agent
CREATE TABLE IF NOT EXISTS memory_patterns (
    id VARCHAR(255) PRIMARY KEY,
    pattern_type VARCHAR(100) NOT NULL,
    content TEXT NOT NULL,
    embedding_id VARCHAR(255),
    success_score FLOAT DEFAULT 0.0,
    usage_count INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT NOW(),
    last_used_at TIMESTAMP
);

CREATE INDEX idx_patterns_type ON memory_patterns(pattern_type);
CREATE INDEX idx_patterns_score ON memory_patterns(success_score);
CREATE INDEX idx_patterns_usage ON memory_patterns(usage_count);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_jobs_updated_at BEFORE UPDATE ON jobs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_artifacts_updated_at BEFORE UPDATE ON artifacts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert initial data
INSERT INTO jobs (id, project_id, status, workflow_stage)
VALUES ('test-job-1', 'test-project-1', 'created', 'initialization')
ON CONFLICT (id) DO NOTHING;

COMMENT ON TABLE jobs IS 'Tracks overall project jobs and their workflow stages';
COMMENT ON TABLE tasks IS 'Individual agent tasks within a job';
COMMENT ON TABLE artifacts IS 'Outputs created by agents (PRDs, code, docs, etc.)';
COMMENT ON TABLE agent_events IS 'Event log for agent activities and debugging';
COMMENT ON TABLE memory_patterns IS 'Stored patterns and templates for reuse';
