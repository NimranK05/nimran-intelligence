-- Run this once in the Supabase SQL editor

CREATE TABLE IF NOT EXISTS seen_tweets (
    tweet_id TEXT PRIMARY KEY,
    seen_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS tweet_picks (
    id            BIGSERIAL PRIMARY KEY,
    tweet_id      TEXT        NOT NULL,
    tweet_url     TEXT,
    author        TEXT,
    text          TEXT,
    score         NUMERIC(6,4),
    pillar        TEXT,
    velocity_raw  NUMERIC(6,4),
    authority_raw NUMERIC(6,4),
    picked_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
