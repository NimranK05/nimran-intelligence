# Twitter Intelligence System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python pipeline that scrapes ~50 tweets via Apify, scores and ranks them, posts the top 3 to Discord, and persists all data to Supabase.

**Architecture:** A single-run CLI script (`main.py`) orchestrates five discrete modules: scraper, deduplicator, scorer, notifier, and persister. Each module is a focused file with no cross-imports except through `main.py`. Supabase stores seen tweet IDs and pick history; Discord receives formatted webhook payloads.

**Tech Stack:** Python 3.11+, `apify-client`, `supabase-py`, `requests`, `python-dotenv`, `numpy` (softmax)

---

## File Structure

```
nimran-intelligence/
├── .env.example
├── requirements.txt
├── README.md
├── main.py                  # Orchestrator — calls each module in order
├── scraper.py               # Fetches ~50 tweets from Apify
├── deduplicator.py          # Filters already-seen tweet IDs via Supabase
├── scorer.py                # Scores + softmax-ranks tweets, picks top 3
├── notifier.py              # Posts top 3 to Discord webhook
├── persister.py             # Saves seen IDs and picks to Supabase
├── supabase_setup.sql       # DDL for both tables
└── tests/
    ├── test_scraper.py
    ├── test_deduplicator.py
    ├── test_scorer.py
    ├── test_notifier.py
    └── test_persister.py
```

---

## Task 1: Project Scaffold

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `supabase_setup.sql`

- [ ] **Step 1: Create `requirements.txt`**

```
apify-client==1.8.1
supabase==2.4.2
requests==2.31.0
python-dotenv==1.0.1
numpy==1.26.4
pytest==8.1.1
pytest-mock==3.14.0
```

- [ ] **Step 2: Create `.env.example`**

```
APIFY_API_TOKEN=your_apify_api_token_here
SUPABASE_URL=https://xxxxxxxxxxxxxxxxxxxx.supabase.co
SUPABASE_KEY=your_supabase_anon_key_here
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

- [ ] **Step 3: Create `supabase_setup.sql`**

```sql
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
```

- [ ] **Step 4: Install dependencies**

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Expected: all packages install without errors.

- [ ] **Step 5: Commit**

```bash
git init
git add requirements.txt .env.example supabase_setup.sql
git commit -m "chore: project scaffold with deps and SQL schema"
```

---

## Task 2: Scraper Module

**Files:**
- Create: `scraper.py`
- Create: `tests/test_scraper.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_scraper.py
from unittest.mock import MagicMock, patch
from scraper import fetch_tweets

SEED_KEYWORDS = ["AI agents", "LLM"]
WATCHED_ACCOUNTS = ["sama", "karpathy"]

def test_fetch_tweets_returns_list_of_dicts(mocker):
    mock_dataset = [
        {
            "id": "123",
            "full_text": "Hello world",
            "user": {"screen_name": "testuser", "followers_count": 1000, "verified": False},
            "retweet_count": 5,
            "favorite_count": 20,
            "created_at": "Mon Apr 06 12:00:00 +0000 2026",
            "url": "https://twitter.com/testuser/status/123",
        }
    ]
    mock_client = MagicMock()
    mock_client.actor.return_value.call.return_value = MagicMock(
        get_dataset=MagicMock(return_value=MagicMock(
            iterate_items=MagicMock(return_value=iter(mock_dataset))
        ))
    )
    mocker.patch("scraper.ApifyClient", return_value=mock_client)

    tweets = fetch_tweets(
        api_token="fake-token",
        keywords=SEED_KEYWORDS,
        accounts=WATCHED_ACCOUNTS,
        max_items=50,
    )

    assert isinstance(tweets, list)
    assert len(tweets) == 1
    assert tweets[0]["id"] == "123"
    assert tweets[0]["text"] == "Hello world"
    assert tweets[0]["author"] == "testuser"
    assert tweets[0]["followers"] == 1000
    assert tweets[0]["retweets"] == 5
    assert tweets[0]["likes"] == 20
    assert tweets[0]["url"] == "https://twitter.com/testuser/status/123"


def test_fetch_tweets_limits_to_max_items(mocker):
    raw = [
        {
            "id": str(i),
            "full_text": f"tweet {i}",
            "user": {"screen_name": "u", "followers_count": 100, "verified": False},
            "retweet_count": 0,
            "favorite_count": 0,
            "created_at": "Mon Apr 06 12:00:00 +0000 2026",
            "url": f"https://twitter.com/u/status/{i}",
        }
        for i in range(80)
    ]
    mock_client = MagicMock()
    mock_client.actor.return_value.call.return_value = MagicMock(
        get_dataset=MagicMock(return_value=MagicMock(
            iterate_items=MagicMock(return_value=iter(raw))
        ))
    )
    mocker.patch("scraper.ApifyClient", return_value=mock_client)

    tweets = fetch_tweets("fake-token", ["AI"], [], max_items=50)
    assert len(tweets) == 50
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_scraper.py -v
```

Expected: `ImportError: No module named 'scraper'`

- [ ] **Step 3: Write `scraper.py`**

```python
# scraper.py
from apify_client import ApifyClient


ACTOR_ID = "apidojo/tweet-scraper"


def fetch_tweets(
    api_token: str,
    keywords: list[str],
    accounts: list[str],
    max_items: int = 50,
) -> list[dict]:
    """
    Calls Apify tweet scraper and returns normalised tweet dicts.

    Each dict has keys:
        id, text, author, followers, verified,
        retweets, likes, created_at, url
    """
    client = ApifyClient(api_token)

    run_input = {
        "searchTerms": keywords,
        "twitterHandles": accounts,
        "maxItems": max_items,
        "lang": "en",
    }

    run = client.actor(ACTOR_ID).call(run_input=run_input)
    dataset = run.get_dataset()

    tweets = []
    for item in dataset.iterate_items():
        if len(tweets) >= max_items:
            break
        tweets.append(_normalise(item))

    return tweets


def _normalise(raw: dict) -> dict:
    user = raw.get("user", {})
    return {
        "id": raw.get("id") or raw.get("id_str", ""),
        "text": raw.get("full_text") or raw.get("text", ""),
        "author": user.get("screen_name", ""),
        "followers": user.get("followers_count", 0),
        "verified": user.get("verified", False),
        "retweets": raw.get("retweet_count", 0),
        "likes": raw.get("favorite_count", 0),
        "created_at": raw.get("created_at", ""),
        "url": raw.get("url", ""),
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_scraper.py -v
```

Expected: 2 tests PASS

- [ ] **Step 5: Commit**

```bash
git add scraper.py tests/test_scraper.py
git commit -m "feat: scraper module with Apify tweet-scraper integration"
```

---

## Task 3: Deduplicator Module

**Files:**
- Create: `deduplicator.py`
- Create: `tests/test_deduplicator.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_deduplicator.py
from unittest.mock import MagicMock
from deduplicator import filter_seen

TWEETS = [
    {"id": "1", "text": "a"},
    {"id": "2", "text": "b"},
    {"id": "3", "text": "c"},
]


def test_filter_seen_removes_known_ids():
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.in_.return_value.execute.return_value.data = [
        {"tweet_id": "1"},
        {"tweet_id": "3"},
    ]

    result = filter_seen(TWEETS, mock_client)

    assert len(result) == 1
    assert result[0]["id"] == "2"


def test_filter_seen_returns_all_when_none_seen():
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.in_.return_value.execute.return_value.data = []

    result = filter_seen(TWEETS, mock_client)

    assert len(result) == 3


def test_filter_seen_returns_empty_when_all_seen():
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.in_.return_value.execute.return_value.data = [
        {"tweet_id": "1"},
        {"tweet_id": "2"},
        {"tweet_id": "3"},
    ]

    result = filter_seen(TWEETS, mock_client)

    assert result == []
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_deduplicator.py -v
```

Expected: `ImportError: No module named 'deduplicator'`

- [ ] **Step 3: Write `deduplicator.py`**

```python
# deduplicator.py


def filter_seen(tweets: list[dict], supabase_client) -> list[dict]:
    """
    Returns only tweets whose IDs are NOT already in the seen_tweets table.
    """
    if not tweets:
        return []

    ids = [t["id"] for t in tweets]

    response = (
        supabase_client
        .table("seen_tweets")
        .select("tweet_id")
        .in_("tweet_id", ids)
        .execute()
    )

    seen_ids = {row["tweet_id"] for row in (response.data or [])}
    return [t for t in tweets if t["id"] not in seen_ids]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_deduplicator.py -v
```

Expected: 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add deduplicator.py tests/test_deduplicator.py
git commit -m "feat: deduplicator filters already-seen tweet IDs via Supabase"
```

---

## Task 4: Scorer Module

**Files:**
- Create: `scorer.py`
- Create: `tests/test_scorer.py`

Scoring formula (all sub-scores normalised 0–1 before weighting):
- **Velocity 35%** — `(retweets * 2 + likes) / MAX_ENGAGEMENT` capped at 1.0
- **Authority 25%** — `log10(followers + 1) / log10(MAX_FOLLOWERS + 1)`; +0.1 bonus if verified (capped at 1.0)
- **Timing 15%** — 1.0 if posted within 6 h, 0.5 if within 24 h, else 0.0
- **Replyability 15%** — heuristic: 1.0 if text ends with `?`, 0.5 if contains `?` anywhere, else 0.0
- **Niche Fit + Opportunity 10%** — 1.0 if any niche keyword present, else 0.0

Pillar tags: tweet with highest velocity → "Breakdown", highest authority → "Stack", else → "Leverage".

- [ ] **Step 1: Write the failing test**

```python
# tests/test_scorer.py
import pytest
from datetime import datetime, timezone, timedelta
from scorer import score_tweets, assign_pillars, softmax_rank

NICHE_KEYWORDS = ["AI", "LLM", "agent", "GPT", "model", "prompt"]

def _now_iso():
    return datetime.now(timezone.utc).strftime("%a %b %d %H:%M:%S +0000 %Y")

def _hours_ago_iso(h):
    dt = datetime.now(timezone.utc) - timedelta(hours=h)
    return dt.strftime("%a %b %d %H:%M:%S +0000 %Y")

TWEET_RECENT_VIRAL = {
    "id": "1", "text": "What does AI do? #LLM",
    "author": "bigaccount", "followers": 50000, "verified": True,
    "retweets": 800, "likes": 2000, "created_at": _hours_ago_iso(2), "url": ""
}
TWEET_OLD_LOW = {
    "id": "2", "text": "Random text",
    "author": "nobody", "followers": 100, "verified": False,
    "retweets": 0, "likes": 1, "created_at": _hours_ago_iso(48), "url": ""
}


def test_score_tweets_returns_scores_for_each():
    result = score_tweets([TWEET_RECENT_VIRAL, TWEET_OLD_LOW], NICHE_KEYWORDS)
    assert len(result) == 2
    # viral tweet should score higher
    scores = {r["id"]: r["score"] for r in result}
    assert scores["1"] > scores["2"]


def test_score_tweets_all_scores_between_0_and_1():
    result = score_tweets([TWEET_RECENT_VIRAL, TWEET_OLD_LOW], NICHE_KEYWORDS)
    for r in result:
        assert 0.0 <= r["score"] <= 1.0


def test_softmax_rank_top3_from_five():
    tweets_with_scores = [
        {"id": str(i), "score": float(i)} for i in range(5)
    ]
    top3 = softmax_rank(tweets_with_scores, top_n=3)
    assert len(top3) == 3
    # top 3 should be highest scores
    assert [t["id"] for t in top3] == ["4", "3", "2"]


def test_assign_pillars_labels_top3():
    top3 = [
        {"id": "1", "velocity_raw": 0.9, "authority_raw": 0.3},
        {"id": "2", "velocity_raw": 0.2, "authority_raw": 0.8},
        {"id": "3", "velocity_raw": 0.4, "authority_raw": 0.4},
    ]
    result = assign_pillars(top3)
    pillar_map = {t["id"]: t["pillar"] for t in result}
    assert pillar_map["1"] == "Breakdown"   # highest velocity
    assert pillar_map["2"] == "Stack"       # highest authority
    assert pillar_map["3"] == "Leverage"    # remainder
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_scorer.py -v
```

Expected: `ImportError: No module named 'scorer'`

- [ ] **Step 3: Write `scorer.py`**

```python
# scorer.py
import math
from datetime import datetime, timezone, timedelta

import numpy as np

NICHE_KEYWORDS_DEFAULT = ["AI", "LLM", "agent", "GPT", "model", "prompt"]

# Normalisation ceilings (adjust if your audience differs)
MAX_ENGAGEMENT = 5000.0    # retweets*2 + likes ceiling
MAX_FOLLOWERS  = 500_000.0  # followers ceiling for log normalisation


def score_tweets(tweets: list[dict], niche_keywords: list[str] = None) -> list[dict]:
    """
    Returns the input tweets enriched with score, velocity_raw, authority_raw.
    """
    keywords = niche_keywords or NICHE_KEYWORDS_DEFAULT
    result = []
    for t in tweets:
        v = _velocity(t)
        a = _authority(t)
        ti = _timing(t)
        r = _replyability(t)
        n = _niche_fit(t, keywords)
        score = v * 0.35 + a * 0.25 + ti * 0.15 + r * 0.15 + n * 0.10
        result.append({**t, "score": round(score, 4), "velocity_raw": v, "authority_raw": a})
    return result


def softmax_rank(scored_tweets: list[dict], top_n: int = 3) -> list[dict]:
    """
    Applies softmax over scores, returns top_n tweets sorted descending by score.
    """
    if not scored_tweets:
        return []
    scores = np.array([t["score"] for t in scored_tweets], dtype=float)
    e = np.exp(scores - scores.max())
    softmax_scores = e / e.sum()
    ranked = sorted(
        zip(softmax_scores, scored_tweets),
        key=lambda x: x[0],
        reverse=True,
    )
    return [t for _, t in ranked[:top_n]]


def assign_pillars(top3: list[dict]) -> list[dict]:
    """
    Tags each tweet with a pillar: Breakdown (highest velocity),
    Stack (highest authority), Leverage (rest).
    """
    if not top3:
        return top3

    breakdown_idx = max(range(len(top3)), key=lambda i: top3[i]["velocity_raw"])
    remaining = [i for i in range(len(top3)) if i != breakdown_idx]
    stack_idx = max(remaining, key=lambda i: top3[i]["authority_raw"]) if remaining else None

    for i, tweet in enumerate(top3):
        if i == breakdown_idx:
            tweet["pillar"] = "Breakdown"
        elif i == stack_idx:
            tweet["pillar"] = "Stack"
        else:
            tweet["pillar"] = "Leverage"

    return top3


# --- sub-scorers ---

def _velocity(t: dict) -> float:
    eng = t["retweets"] * 2 + t["likes"]
    return min(eng / MAX_ENGAGEMENT, 1.0)


def _authority(t: dict) -> float:
    score = math.log10(t["followers"] + 1) / math.log10(MAX_FOLLOWERS + 1)
    if t.get("verified"):
        score += 0.1
    return min(score, 1.0)


def _timing(t: dict) -> float:
    try:
        created = datetime.strptime(t["created_at"], "%a %b %d %H:%M:%S +0000 %Y")
        created = created.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return 0.0
    age = datetime.now(timezone.utc) - created
    if age <= timedelta(hours=6):
        return 1.0
    if age <= timedelta(hours=24):
        return 0.5
    return 0.0


def _replyability(t: dict) -> float:
    text = t.get("text", "")
    if text.endswith("?"):
        return 1.0
    if "?" in text:
        return 0.5
    return 0.0


def _niche_fit(t: dict, keywords: list[str]) -> float:
    text_lower = t.get("text", "").lower()
    for kw in keywords:
        if kw.lower() in text_lower:
            return 1.0
    return 0.0
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_scorer.py -v
```

Expected: 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add scorer.py tests/test_scorer.py
git commit -m "feat: scorer with velocity/authority/timing/replyability/niche, softmax ranking, pillar tags"
```

---

## Task 5: Notifier Module

**Files:**
- Create: `notifier.py`
- Create: `tests/test_notifier.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_notifier.py
from unittest.mock import patch, MagicMock
from notifier import post_to_discord

TOP3 = [
    {
        "id": "1", "text": "AI agents are taking over!", "author": "karpathy",
        "url": "https://twitter.com/karpathy/status/1",
        "score": 0.8712, "pillar": "Breakdown",
        "velocity_raw": 0.91, "authority_raw": 0.75,
    },
    {
        "id": "2", "text": "LLMs are just autocomplete", "author": "sama",
        "url": "https://twitter.com/sama/status/2",
        "score": 0.7203, "pillar": "Stack",
        "velocity_raw": 0.55, "authority_raw": 0.88,
    },
    {
        "id": "3", "text": "What prompt do you use daily?", "author": "levelsio",
        "url": "https://twitter.com/levelsio/status/3",
        "score": 0.6541, "pillar": "Leverage",
        "velocity_raw": 0.40, "authority_raw": 0.50,
    },
]


def test_post_to_discord_calls_webhook(mocker):
    mock_post = mocker.patch("notifier.requests.post")
    mock_post.return_value.status_code = 204

    post_to_discord(TOP3, webhook_url="https://discord.com/api/webhooks/fake")

    assert mock_post.called
    args, kwargs = mock_post.call_args
    payload = kwargs["json"]
    assert "embeds" in payload
    assert len(payload["embeds"]) == 3


def test_post_to_discord_embed_contains_required_fields(mocker):
    mock_post = mocker.patch("notifier.requests.post")
    mock_post.return_value.status_code = 204

    post_to_discord(TOP3, webhook_url="https://discord.com/api/webhooks/fake")

    payload = mock_post.call_args[1]["json"]
    first_embed = payload["embeds"][0]

    assert "Breakdown" in first_embed["title"]
    assert "karpathy" in first_embed["description"]
    assert "0.87" in first_embed["description"] or "87" in first_embed["description"]
    # velocity and authority shown
    assert any("Velocity" in str(f) for f in first_embed["fields"])
    assert any("Authority" in str(f) for f in first_embed["fields"])


def test_post_to_discord_raises_on_failure(mocker):
    mock_post = mocker.patch("notifier.requests.post")
    mock_post.return_value.status_code = 400
    mock_post.return_value.text = "Bad Request"

    import pytest
    with pytest.raises(RuntimeError, match="Discord webhook failed"):
        post_to_discord(TOP3, webhook_url="https://discord.com/api/webhooks/fake")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_notifier.py -v
```

Expected: `ImportError: No module named 'notifier'`

- [ ] **Step 3: Write `notifier.py`**

```python
# notifier.py
import requests

PILLAR_COLOURS = {
    "Breakdown": 0xE74C3C,  # red
    "Stack":     0x3498DB,  # blue
    "Leverage":  0x2ECC71,  # green
}


def post_to_discord(top3: list[dict], webhook_url: str) -> None:
    """
    Posts top 3 tweets to Discord as a single webhook message with 3 embeds.
    Raises RuntimeError if Discord returns a non-2xx status.
    """
    embeds = [_build_embed(rank, tweet) for rank, tweet in enumerate(top3, start=1)]
    payload = {"username": "Tweet Scout", "embeds": embeds}

    resp = requests.post(webhook_url, json=payload, timeout=10)
    if not (200 <= resp.status_code < 300):
        raise RuntimeError(f"Discord webhook failed: {resp.status_code} — {resp.text}")


def _build_embed(rank: int, tweet: dict) -> dict:
    pillar = tweet.get("pillar", "Leverage")
    score_pct = int(tweet["score"] * 100)
    velocity_pct = int(tweet["velocity_raw"] * 100)
    authority_pct = int(tweet["authority_raw"] * 100)

    return {
        "title": f"#{rank} [{pillar}] — Score: {score_pct}%",
        "description": (
            f"**@{tweet['author']}**\n\n"
            f"{tweet['text']}\n\n"
            f"[View tweet]({tweet['url']})"
        ),
        "color": PILLAR_COLOURS.get(pillar, 0x95A5A6),
        "fields": [
            {"name": "Velocity", "value": f"{velocity_pct}%", "inline": True},
            {"name": "Authority", "value": f"{authority_pct}%", "inline": True},
        ],
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_notifier.py -v
```

Expected: 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add notifier.py tests/test_notifier.py
git commit -m "feat: Discord notifier posts top 3 tweets as embeds with pillar/score/breakdown"
```

---

## Task 6: Persister Module

**Files:**
- Create: `persister.py`
- Create: `tests/test_persister.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_persister.py
from unittest.mock import MagicMock
from persister import save_seen_tweets, save_picks

TWEETS = [
    {"id": "1", "text": "a", "author": "u1", "url": ""},
    {"id": "2", "text": "b", "author": "u2", "url": ""},
]
TOP3 = [
    {
        "id": "1", "text": "a", "author": "u1", "url": "https://t.co/1",
        "score": 0.85, "pillar": "Breakdown",
        "velocity_raw": 0.9, "authority_raw": 0.7,
    }
]


def test_save_seen_tweets_upserts_all_ids():
    mock_client = MagicMock()
    mock_client.table.return_value.upsert.return_value.execute.return_value = MagicMock()

    save_seen_tweets(TWEETS, mock_client)

    mock_client.table.assert_called_with("seen_tweets")
    call_args = mock_client.table.return_value.upsert.call_args[0][0]
    ids = [row["tweet_id"] for row in call_args]
    assert set(ids) == {"1", "2"}


def test_save_picks_inserts_top3():
    mock_client = MagicMock()
    mock_client.table.return_value.insert.return_value.execute.return_value = MagicMock()

    save_picks(TOP3, mock_client)

    mock_client.table.assert_called_with("tweet_picks")
    call_args = mock_client.table.return_value.insert.call_args[0][0]
    assert len(call_args) == 1
    assert call_args[0]["tweet_id"] == "1"
    assert call_args[0]["pillar"] == "Breakdown"
    assert call_args[0]["score"] == 0.85
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_persister.py -v
```

Expected: `ImportError: No module named 'persister'`

- [ ] **Step 3: Write `persister.py`**

```python
# persister.py


def save_seen_tweets(tweets: list[dict], supabase_client) -> None:
    """
    Upserts all tweet IDs into seen_tweets so they are skipped next run.
    """
    if not tweets:
        return
    rows = [{"tweet_id": t["id"]} for t in tweets]
    supabase_client.table("seen_tweets").upsert(rows).execute()


def save_picks(top3: list[dict], supabase_client) -> None:
    """
    Inserts the top-3 picks into tweet_picks for history.
    """
    if not top3:
        return
    rows = [
        {
            "tweet_id":      t["id"],
            "tweet_url":     t.get("url", ""),
            "author":        t.get("author", ""),
            "text":          t.get("text", ""),
            "score":         t["score"],
            "pillar":        t.get("pillar", ""),
            "velocity_raw":  t["velocity_raw"],
            "authority_raw": t["authority_raw"],
        }
        for t in top3
    ]
    supabase_client.table("tweet_picks").insert(rows).execute()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_persister.py -v
```

Expected: 2 tests PASS

- [ ] **Step 5: Commit**

```bash
git add persister.py tests/test_persister.py
git commit -m "feat: persister saves seen IDs and picks to Supabase"
```

---

## Task 7: Orchestrator (`main.py`)

**Files:**
- Create: `main.py`

No unit tests for the orchestrator — it is a thin wiring layer. Integration is verified by a manual dry-run step.

- [ ] **Step 1: Write `main.py`**

```python
# main.py
import os
from dotenv import load_dotenv
from supabase import create_client

from scraper      import fetch_tweets
from deduplicator import filter_seen
from scorer       import score_tweets, softmax_rank, assign_pillars
from notifier     import post_to_discord
from persister    import save_seen_tweets, save_picks

# --- Configuration ---
SEED_KEYWORDS = [
    "AI agents", "LLM", "prompt engineering", "GPT-4o",
    "Claude", "Gemini", "RAG", "fine-tuning",
]
WATCHED_ACCOUNTS = [
    "sama", "karpathy", "emollick", "swyx",
    "hwchase17", "simonw", "levelsio",
]
NICHE_KEYWORDS = ["AI", "LLM", "agent", "GPT", "model", "prompt", "RAG", "Claude"]


def main():
    load_dotenv()

    apify_token   = os.environ["APIFY_API_TOKEN"]
    supabase_url  = os.environ["SUPABASE_URL"]
    supabase_key  = os.environ["SUPABASE_KEY"]
    webhook_url   = os.environ["DISCORD_WEBHOOK_URL"]

    sb = create_client(supabase_url, supabase_key)

    print("Fetching tweets from Apify...")
    raw_tweets = fetch_tweets(apify_token, SEED_KEYWORDS, WATCHED_ACCOUNTS, max_items=50)
    print(f"  Fetched: {len(raw_tweets)}")

    print("Deduplicating...")
    new_tweets = filter_seen(raw_tweets, sb)
    print(f"  New (unseen): {len(new_tweets)}")

    if not new_tweets:
        print("No new tweets to process. Exiting.")
        return

    print("Scoring...")
    scored = score_tweets(new_tweets, NICHE_KEYWORDS)

    print("Ranking (softmax top 3)...")
    top3 = softmax_rank(scored, top_n=3)
    top3 = assign_pillars(top3)

    for t in top3:
        print(f"  [{t['pillar']}] @{t['author']} score={t['score']} — {t['text'][:60]}")

    print("Posting to Discord...")
    post_to_discord(top3, webhook_url)
    print("  Posted.")

    print("Saving to Supabase...")
    save_seen_tweets(raw_tweets, sb)   # mark ALL fetched as seen
    save_picks(top3, sb)
    print("  Saved.")

    print("Done.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the full test suite**

```bash
pytest tests/ -v
```

Expected: all 12 tests PASS

- [ ] **Step 3: Commit**

```bash
git add main.py
git commit -m "feat: orchestrator wires scraper → dedup → scorer → notifier → persister"
```

---

## Task 8: README

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write `README.md`**

```markdown
# Nimran Twitter Intelligence

Fetches ~50 tweets via Apify, scores them, posts the top 3 to Discord, and saves everything to Supabase.

## Quick Start

### 1. Clone & install

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Supabase setup

1. Create a free project at https://supabase.com
2. Open the SQL Editor and run `supabase_setup.sql`

### 3. Apify setup

1. Sign up at https://apify.com
2. Copy your API token from **Settings → Integrations**

### 4. Discord webhook

1. In your Discord server: **Server Settings → Integrations → Webhooks → New Webhook**
2. Copy the webhook URL

### 5. Configure environment

```bash
cp .env.example .env
# Fill in all four values in .env
```

### 6. Run

```bash
python main.py
```

## Scoring Breakdown

| Component          | Weight | Signal                                  |
|--------------------|--------|-----------------------------------------|
| Velocity           | 35%    | Retweets × 2 + Likes (cap 5 000)       |
| Authority          | 25%    | log₁₀(followers); +10% if verified     |
| Timing             | 15%    | 1.0 < 6 h old · 0.5 < 24 h · 0.0 else |
| Replyability       | 15%    | Ends with ? → 1.0 · Contains ? → 0.5  |
| Niche Fit          | 10%    | Keyword match on AI/LLM/agent/etc.     |

Top 3 selected by softmax ranking. Pillar tags: **Breakdown** (highest velocity), **Stack** (highest authority), **Leverage** (other).

## Customisation

Edit the top of `main.py` to change:
- `SEED_KEYWORDS` — search terms passed to Apify
- `WATCHED_ACCOUNTS` — Twitter handles to include
- `NICHE_KEYWORDS` — keywords used for niche-fit scoring

Adjust `MAX_ENGAGEMENT` and `MAX_FOLLOWERS` in `scorer.py` to tune normalisation ceilings for your audience.
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: README with setup instructions and scoring table"
```

---

## Self-Review

**Spec coverage check:**
1. ✅ Calls Apify tweet scraper for ~50 tweets with keywords + accounts → `scraper.py` Task 2
2. ✅ Deduplicates against Supabase — `deduplicator.py` Task 3
3. ✅ Scores: Velocity 35%, Authority 25%, Timing 15%, Replyability 15%, Niche 10% → `scorer.py` Task 4
4. ✅ Softmax ranking, top 3 → `softmax_rank()` Task 4
5. ✅ Discord webhook with tweet, score, pillar, velocity/authority breakdown → `notifier.py` Task 5
6. ✅ Saves all seen tweets + picks to Supabase → `persister.py` Task 6
7. ✅ All four env vars used in `main.py` Task 7
8. ✅ SQL schema for both tables → Task 1
9. ✅ requirements.txt, .env.example, README → Tasks 1 & 8

**Placeholder scan:** No TBDs, no "add error handling" without specifics, no forward references to undefined types. All code blocks are complete.

**Type consistency:**
- `fetch_tweets` → returns `list[dict]` with keys `id, text, author, followers, verified, retweets, likes, created_at, url` — used consistently in scorer, notifier, persister.
- `score_tweets` → adds `score, velocity_raw, authority_raw` — consumed by `softmax_rank`, `assign_pillars`, `notifier`, `persister`.
- `assign_pillars` → adds `pillar` — consumed by `notifier` and `persister`.
