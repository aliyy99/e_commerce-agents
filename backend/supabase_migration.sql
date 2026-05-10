-- ═══════════════════════════════════════════════════════════
-- ShopSage AI  –  Supabase Database Schema
-- Run this in: Supabase Dashboard → SQL Editor
-- ═══════════════════════════════════════════════════════════

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ─────────────────────────────────────────────────────────
-- Table: analysis_results
-- Stores the aggregated output of each orchestration run.
-- ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS analysis_results (
    id               UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id       TEXT,
    query            TEXT         NOT NULL,
    category         TEXT         NOT NULL DEFAULT 'other',

    -- Agent outputs stored as JSONB for flexibility
    vision_result    JSONB,
    analyst_result   JSONB,
    style_result     JSONB,

    created_at       TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- Index for fast product lookups (used by fetch_cached_analysis)
CREATE INDEX IF NOT EXISTS idx_analysis_product_id
    ON analysis_results (product_id, created_at DESC);

-- ─────────────────────────────────────────────────────────
-- Storage bucket: shopsage-images
-- Stores Visualizer Agent generated images.
-- ─────────────────────────────────────────────────────────
-- Run via Supabase Dashboard > Storage > New Bucket:
--   Name: shopsage-images
--   Public: true
--   Allowed MIME types: image/png, image/jpeg, image/webp

-- Or via SQL (Supabase Storage API):
INSERT INTO storage.buckets (id, name, public)
VALUES ('shopsage-images', 'shopsage-images', true)
ON CONFLICT (id) DO NOTHING;

-- ─────────────────────────────────────────────────────────
-- Row Level Security (RLS)
-- Enable for production; disable during local dev.
-- ─────────────────────────────────────────────────────────
ALTER TABLE analysis_results ENABLE ROW LEVEL SECURITY;

-- Service key bypass (backend writes use service key)
CREATE POLICY "service_key_full_access"
    ON analysis_results
    FOR ALL
    USING (true)      -- Allow service key to bypass
    WITH CHECK (true);
