-- Migration: Add skill allowlist tables for per-agent skill permissions

-- Agent skill allowlist table - controls which agents can use which skills
CREATE TABLE IF NOT EXISTS agent_skill_allowlist (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(100) NOT NULL,
    skill_name VARCHAR(255) NOT NULL,
    allowed BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(255),
    notes TEXT,
    UNIQUE(agent_id, skill_name)
);

CREATE INDEX idx_allowlist_agent_id ON agent_skill_allowlist(agent_id);
CREATE INDEX idx_allowlist_skill_name ON agent_skill_allowlist(skill_name);
CREATE INDEX idx_allowlist_allowed ON agent_skill_allowlist(allowed);

-- Capability mapping table - maps capabilities to skills
CREATE TABLE IF NOT EXISTS capability_skill_mapping (
    id SERIAL PRIMARY KEY,
    capability_name VARCHAR(255) NOT NULL,
    skill_name VARCHAR(255) NOT NULL,
    priority INTEGER DEFAULT 10,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(capability_name, skill_name)
);

CREATE INDEX idx_capability_mapping_capability ON capability_skill_mapping(capability_name);
CREATE INDEX idx_capability_mapping_skill ON capability_skill_mapping(skill_name);
CREATE INDEX idx_capability_mapping_priority ON capability_skill_mapping(priority);

-- Trigger for updated_at on capability mapping
CREATE TRIGGER update_capability_mapping_updated_at 
BEFORE UPDATE ON capability_skill_mapping
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Comments
COMMENT ON TABLE agent_skill_allowlist IS 'Per-agent skill permission allowlist';
COMMENT ON TABLE capability_skill_mapping IS 'Maps capability names to available skills with priority';

COMMENT ON COLUMN agent_skill_allowlist.agent_id IS 'Agent identifier (e.g., developer_agent)';
COMMENT ON COLUMN agent_skill_allowlist.skill_name IS 'Skill name from registry';
COMMENT ON COLUMN agent_skill_allowlist.allowed IS 'Whether agent is allowed to use this skill';

COMMENT ON COLUMN capability_skill_mapping.capability_name IS 'Capability identifier (e.g., ui-design)';
COMMENT ON COLUMN capability_skill_mapping.skill_name IS 'Skill that provides this capability';
COMMENT ON COLUMN capability_skill_mapping.priority IS 'Priority for skill selection (lower = higher priority)';
