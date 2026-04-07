-- Run this in the Supabase SQL editor to set up (or reset) the schema.
-- WARNING: DROP statements will remove existing data in these tables.

-- ─────────────────────────────────────────────────────────────────────────────
-- UPGRADE PATH (existing installation — run these instead of the full reset):
--
--   ALTER TABLE tweet_picks ADD COLUMN IF NOT EXISTS discord_message_id TEXT;
--
--   CREATE TABLE IF NOT EXISTS account_feedback (
--     id                   SERIAL PRIMARY KEY,
--     handle               TEXT UNIQUE NOT NULL,
--     shown_count          INT         NOT NULL DEFAULT 0,
--     used_count           INT         NOT NULL DEFAULT 0,
--     authority_multiplier FLOAT       NOT NULL DEFAULT 1.0,
--     updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
--   );
--
--   CREATE TABLE IF NOT EXISTS pick_feedback (
--     id                   SERIAL PRIMARY KEY,
--     tweet_url            TEXT        NOT NULL,
--     discord_message_id   TEXT        UNIQUE NOT NULL,
--     used                 BOOLEAN     NOT NULL,
--     logged_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
--   );
-- ─────────────────────────────────────────────────────────────────────────────

DROP TABLE IF EXISTS pick_feedback;
DROP TABLE IF EXISTS account_feedback;
DROP TABLE IF EXISTS seen_tweets;
DROP TABLE IF EXISTS tweet_picks;

CREATE TABLE seen_tweets (
    tweet_id TEXT PRIMARY KEY,
    seen_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE tweet_picks (
    id                   BIGSERIAL   PRIMARY KEY,
    tweet_id             TEXT        NOT NULL,
    tweet_url            TEXT,
    author               TEXT,
    text                 TEXT,
    score                NUMERIC(6,4),
    pillar               TEXT,
    velocity_raw         NUMERIC(6,4),
    authority_raw        NUMERIC(6,4),
    likes                INT,
    bookmarks            INT,
    views                INT,
    discord_message_id   TEXT,
    picked_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Tracks how often each account's picks are shown vs actually used.
-- authority_multiplier is updated weekly by reweighter.py.
CREATE TABLE account_feedback (
    id                   SERIAL      PRIMARY KEY,
    handle               TEXT        UNIQUE NOT NULL,
    shown_count          INT         NOT NULL DEFAULT 0,
    used_count           INT         NOT NULL DEFAULT 0,
    authority_multiplier FLOAT       NOT NULL DEFAULT 1.0,
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- One row per Discord message that received a ✅ or ❌ reaction.
CREATE TABLE pick_feedback (
    id                   SERIAL      PRIMARY KEY,
    tweet_url            TEXT        NOT NULL,
    discord_message_id   TEXT        UNIQUE NOT NULL,
    used                 BOOLEAN     NOT NULL,
    logged_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
