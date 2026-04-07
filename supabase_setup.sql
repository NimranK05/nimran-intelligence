-- Run this in the Supabase SQL editor to set up (or reset) the schema.
-- WARNING: DROP statements will remove existing data in these tables.

DROP TABLE IF EXISTS seen_tweets;
DROP TABLE IF EXISTS tweet_picks;

CREATE TABLE seen_tweets (
    tweet_id TEXT PRIMARY KEY,
    seen_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE tweet_picks (
    id            BIGSERIAL PRIMARY KEY,
    tweet_id      TEXT        NOT NULL,
    tweet_url     TEXT,
    author        TEXT,
    text          TEXT,
    score         NUMERIC(6,4),
    pillar        TEXT,
    velocity_raw  NUMERIC(6,4),
    authority_raw NUMERIC(6,4),
    likes         INT,
    bookmarks     INT,
    views         INT,
    picked_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
