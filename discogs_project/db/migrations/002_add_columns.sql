-- =====================================================================================
-- Migration 002: Add Missing Columns
-- =====================================================================================
-- Idempotent ALTER TABLE blocks for columns that may be absent on older installs.
-- All changes use DO $$ IF NOT EXISTS blocks — never drops anything.
-- =====================================================================================

SET search_path TO collection_data, public;

-- =====================================================================================
-- SECTION 1: releases table — community stats columns
-- =====================================================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'collection_data'
          AND table_name   = 'releases'
          AND column_name  = 'community_have_count'
    ) THEN
        ALTER TABLE releases ADD COLUMN community_have_count INTEGER DEFAULT 0;
        RAISE NOTICE 'Added community_have_count to releases';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'collection_data'
          AND table_name   = 'releases'
          AND column_name  = 'community_want_count'
    ) THEN
        ALTER TABLE releases ADD COLUMN community_want_count INTEGER DEFAULT 0;
        RAISE NOTICE 'Added community_want_count to releases';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'collection_data'
          AND table_name   = 'releases'
          AND column_name  = 'community_average_rating'
    ) THEN
        ALTER TABLE releases ADD COLUMN community_average_rating DECIMAL(3,2) DEFAULT 0.0;
        RAISE NOTICE 'Added community_average_rating to releases';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'collection_data'
          AND table_name   = 'releases'
          AND column_name  = 'community_rating_count'
    ) THEN
        ALTER TABLE releases ADD COLUMN community_rating_count INTEGER DEFAULT 0;
        RAISE NOTICE 'Added community_rating_count to releases';
    END IF;
END $$;

-- =====================================================================================
-- SECTION 2: releases table — copies, instance_ids, producers, stats
-- =====================================================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'collection_data'
          AND table_name   = 'releases'
          AND column_name  = 'copies_count'
    ) THEN
        ALTER TABLE releases ADD COLUMN copies_count INTEGER DEFAULT 1;
        RAISE NOTICE 'Added copies_count to releases';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'collection_data'
          AND table_name   = 'releases'
          AND column_name  = 'instance_ids'
    ) THEN
        ALTER TABLE releases ADD COLUMN instance_ids JSONB;
        RAISE NOTICE 'Added instance_ids to releases';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'collection_data'
          AND table_name   = 'releases'
          AND column_name  = 'producers'
    ) THEN
        ALTER TABLE releases ADD COLUMN producers JSONB;
        RAISE NOTICE 'Added producers to releases';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'collection_data'
          AND table_name   = 'releases'
          AND column_name  = 'stats_last_updated'
    ) THEN
        ALTER TABLE releases ADD COLUMN stats_last_updated TIMESTAMP;
        RAISE NOTICE 'Added stats_last_updated to releases';
    END IF;
END $$;

-- =====================================================================================
-- SECTION 3: artwork table — thumbnail support
-- =====================================================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'collection_data'
          AND table_name   = 'artwork'
          AND column_name  = 'thumbnail_file_path'
    ) THEN
        ALTER TABLE artwork ADD COLUMN thumbnail_file_path TEXT;
        RAISE NOTICE 'Added thumbnail_file_path to artwork';
    END IF;
END $$;

-- =====================================================================================
-- SECTION 4: marketplace_stats_dim — create if not present
-- =====================================================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'collection_data'
          AND table_name   = 'marketplace_stats_dim'
    ) THEN
        CREATE TABLE marketplace_stats_dim (
            discogs_release_id  INTEGER PRIMARY KEY,
            last_sold_date      DATE,
            low_sold_price      DECIMAL(10,2),
            high_sold_price     DECIMAL(10,2),
            currency            VARCHAR(10),
            as_of               TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            notes               TEXT
        );
        RAISE NOTICE 'Created marketplace_stats_dim';
    END IF;
END $$;
