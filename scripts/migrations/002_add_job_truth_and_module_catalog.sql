-- Add canonical job truth table and module catalog

CREATE TABLE IF NOT EXISTS job_truth (
    job_id VARCHAR(255) PRIMARY KEY REFERENCES jobs(id) ON DELETE CASCADE,
    requirements TEXT NOT NULL,
    requirements_hash VARCHAR(64) NOT NULL,
    prd_content TEXT NOT NULL,
    prd_hash VARCHAR(64) NOT NULL,
    prd_artifact_id VARCHAR(255),
    approved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_job_truth_prd_hash ON job_truth(prd_hash);

CREATE TRIGGER update_job_truth_updated_at
BEFORE UPDATE ON job_truth
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TABLE IF NOT EXISTS module_catalog (
    id SERIAL PRIMARY KEY,
    module_id VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    capabilities JSONB DEFAULT '[]'::jsonb,
    owner VARCHAR(255),
    description TEXT,
    version INTEGER DEFAULT 1,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_module_catalog_module_id ON module_catalog(module_id);
CREATE INDEX IF NOT EXISTS idx_module_catalog_active ON module_catalog(active);

CREATE TRIGGER update_module_catalog_updated_at
BEFORE UPDATE ON module_catalog
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
