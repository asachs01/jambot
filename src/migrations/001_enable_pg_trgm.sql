-- Enable pg_trgm extension for fuzzy text matching
-- This migration is idempotent and safe to run multiple times

-- Enable the pg_trgm extension
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Create GIN index on chord_charts.title for trigram similarity search
CREATE INDEX IF NOT EXISTS idx_chord_charts_title_trgm
ON chord_charts USING gin (title gin_trgm_ops);
