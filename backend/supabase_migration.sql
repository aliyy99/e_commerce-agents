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
-- Table: favorites
-- Stores user-favorited products for the Profile dashboard.
-- ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS favorites (
    id               UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id          TEXT         NOT NULL,
    product_name     TEXT         NOT NULL,
    price            NUMERIC(12,2) NOT NULL,
    url              TEXT         NOT NULL,
    image_url        TEXT,
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_favorites_user_id
    ON favorites (user_id, created_at DESC);


-- ─────────────────────────────────────────────────────────
-- Table: price_alerts
-- Stores user-defined price drop alerts for background monitoring.
-- ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS price_alerts (
    id               UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id          TEXT         NOT NULL,
    product_id       TEXT         NOT NULL,
    product_name     TEXT         NOT NULL,
    target_price     NUMERIC(12,2) NOT NULL,
    current_price    NUMERIC(12,2) NOT NULL,
    is_active        BOOLEAN      NOT NULL DEFAULT true,
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT now(),
    triggered_at     TIMESTAMPTZ  -- When the alert was triggered (price dropped)
);

CREATE INDEX IF NOT EXISTS idx_price_alerts_user_active
    ON price_alerts (user_id, is_active, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_price_alerts_product
    ON price_alerts (product_id, is_active);


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
ALTER TABLE favorites        ENABLE ROW LEVEL SECURITY;
ALTER TABLE price_alerts     ENABLE ROW LEVEL SECURITY;

-- Service key bypass (backend writes use service key)
CREATE POLICY "service_key_full_access"
    ON analysis_results
    FOR ALL
    USING (true)      -- Allow service key to bypass
    WITH CHECK (true);

CREATE POLICY "service_key_full_access_favorites"
    ON favorites
    FOR ALL
    USING (true)
    WITH CHECK (true);

CREATE POLICY "service_key_full_access_alerts"
    ON price_alerts
    FOR ALL
    USING (true)
    WITH CHECK (true);
