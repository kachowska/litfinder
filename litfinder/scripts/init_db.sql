-- LitFinder Database Initialization
-- PostgreSQL 16 with pgvector extension

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Set timezone
SET timezone = 'UTC';

-- Create text search configuration for Russian
CREATE TEXT SEARCH CONFIGURATION IF NOT EXISTS russian_config (COPY = pg_catalog.russian);

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE litfinder TO litfinder;

-- Log successful initialization
DO $$
BEGIN
  RAISE NOTICE 'LitFinder database initialized successfully!';
  RAISE NOTICE 'Extensions enabled: uuid-ossp, vector';
END $$;
