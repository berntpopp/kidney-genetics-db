-- Kidney Genetics Database Schema
-- Initialize database with tables and indexes

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users for basic auth
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    is_admin BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Genes master table
CREATE TABLE IF NOT EXISTS genes (
    id SERIAL PRIMARY KEY,
    hgnc_id VARCHAR(50) UNIQUE,
    approved_symbol VARCHAR(100) NOT NULL,
    aliases TEXT[],
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Gene evidence from sources
CREATE TABLE IF NOT EXISTS gene_evidence (
    id SERIAL PRIMARY KEY,
    gene_id INTEGER REFERENCES genes(id) ON DELETE CASCADE,
    source_name VARCHAR(100) NOT NULL,
    source_detail VARCHAR(255),
    evidence_data JSONB NOT NULL,
    evidence_date DATE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Final curated gene list
CREATE TABLE IF NOT EXISTS gene_curations (
    id SERIAL PRIMARY KEY,
    gene_id INTEGER REFERENCES genes(id) UNIQUE,
    evidence_count INTEGER DEFAULT 0,
    source_count INTEGER DEFAULT 0,
    
    -- Core kidney genetics fields
    panelapp_panels TEXT[],
    literature_refs TEXT[],
    diagnostic_panels TEXT[],
    hpo_terms TEXT[],
    pubtator_pmids TEXT[],
    
    -- Annotations
    omim_data JSONB,
    clinvar_data JSONB,
    constraint_scores JSONB,
    expression_data JSONB,
    
    -- Summary scores
    evidence_score NUMERIC(5,2),
    classification VARCHAR(50),
    
    last_updated TIMESTAMPTZ DEFAULT NOW()
);

-- Pipeline runs tracking
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id SERIAL PRIMARY KEY,
    status VARCHAR(50) DEFAULT 'running',
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    stats JSONB,
    error_log TEXT
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_genes_symbol ON genes(approved_symbol);
CREATE INDEX IF NOT EXISTS idx_genes_hgnc ON genes(hgnc_id);
CREATE INDEX IF NOT EXISTS idx_evidence_gene ON gene_evidence(gene_id);
CREATE INDEX IF NOT EXISTS idx_evidence_source ON gene_evidence(source_name);
CREATE INDEX IF NOT EXISTS idx_curations_score ON gene_curations(evidence_score DESC);
CREATE INDEX IF NOT EXISTS idx_curations_gene ON gene_curations(gene_id);

-- Insert default admin user (password: admin123 - change in production!)
-- bcrypt hash of 'admin123'
INSERT INTO users (email, hashed_password, is_admin) 
VALUES ('admin@kidney-genetics.org', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY.MuU6YE/R5tIa', true)
ON CONFLICT (email) DO NOTHING;

-- Sample data for testing (optional - remove in production)
INSERT INTO genes (hgnc_id, approved_symbol, aliases)
VALUES 
    ('HGNC:9008', 'PKD1', ARRAY['PBP', 'Pc-1', 'TRPP1']),
    ('HGNC:9009', 'PKD2', ARRAY['PKD4', 'TRPP2', 'PC2']),
    ('HGNC:7989', 'NPHS1', ARRAY['CNF', 'NPHN']),
    ('HGNC:13349', 'NPHS2', ARRAY['PDCN', 'SRN1'])
ON CONFLICT (hgnc_id) DO NOTHING;