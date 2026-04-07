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
