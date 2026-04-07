import os
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from supabase import create_client

from scraper      import fetch_tweets
from deduplicator import filter_seen
from scorer       import score_tweets, softmax_rank, assign_pillars
from notifier     import post_to_discord
from persister    import save_seen_tweets, save_picks

MAX_AGE_HOURS = 36  # drop tweets older than this

# --- Configuration ---
SEED_KEYWORDS = [
    "AI agents OR Claude OR GPT OR Gemini OR \"AI tools\" OR \"AI for business\" OR \"AI automation\" OR \"LLM\" lang:en min_faves:50",
]
WATCHED_ACCOUNTS = [
    # AI companies — announcements here = content ideas
    "AnthropicAI", "OpenAI", "GoogleDeepMind", "xai",
    # Key voices — insight, takes, industry moves
    "sama", "karpathy", "emollick", "levelsio",
    # Reference creators — study what they cover
    "gregisenberg", "nicksaraevv", "heyiamnate",
]
NICHE_KEYWORDS = [
    "AI", "LLM", "Claude", "GPT", "Gemini", "agent", "model",
    "automation", "Anthropic", "OpenAI", "Grok", "Copilot",
    "prompt", "RAG", "fine-tun", "inference", "token",
]


def main():
    load_dotenv()

    apify_token   = os.environ["APIFY_API_TOKEN"]
    supabase_url  = os.environ["SUPABASE_URL"]
    supabase_key  = os.environ["SUPABASE_KEY"]
    webhook_url   = os.environ["DISCORD_WEBHOOK_URL"]

    sb = create_client(supabase_url, supabase_key)

    # Build since: date — Twitter operator narrows fetch to last ~36h at source
    since_date = (datetime.now(timezone.utc) - timedelta(hours=MAX_AGE_HOURS)).strftime("%Y-%m-%d")
    keywords_with_since = [f"{SEED_KEYWORDS[0]} since:{since_date}"]

    print("Fetching tweets from Apify...")
    raw_tweets = fetch_tweets(apify_token, keywords_with_since, WATCHED_ACCOUNTS, max_items=50)
    print(f"  Fetched: {len(raw_tweets)}")

    print("Filtering by age (last 36h)...")
    cutoff = datetime.now(timezone.utc) - timedelta(hours=MAX_AGE_HOURS)
    raw_tweets = [t for t in raw_tweets if _parse_age(t["created_at"]) >= cutoff]
    print(f"  Within 36h: {len(raw_tweets)}")

    if not raw_tweets:
        print("No recent tweets found. Exiting.")
        return

    print("Deduplicating...")
    new_tweets = filter_seen(raw_tweets, sb)
    print(f"  New (unseen): {len(new_tweets)}")

    if not new_tweets:
        print("No new tweets to process. Exiting.")
        return

    print("Filtering to niche...")
    new_tweets = [
        t for t in new_tweets
        if any(kw.lower() in t["text"].lower() for kw in NICHE_KEYWORDS)
    ]
    print(f"  In-niche: {len(new_tweets)}")

    if not new_tweets:
        print("No in-niche tweets to process. Exiting.")
        return

    print("Loading account authority multipliers...")
    account_multipliers = _load_multipliers(sb)
    print(f"  Loaded {len(account_multipliers)} multipliers.")

    print("Scoring...")
    scored = score_tweets(new_tweets, NICHE_KEYWORDS, account_multipliers)

    print("Ranking (softmax top 3)...")
    top3 = softmax_rank(scored, top_n=3)
    top3 = assign_pillars(top3)

    for t in top3:
        print(f"  [{t['pillar']}] @{t['author']} score={t['score']} — {t['text'][:60]}")

    print("Posting to Discord...")
    message_ids = post_to_discord(top3, webhook_url)
    print("  Posted.")

    print("Saving to Supabase...")
    save_seen_tweets(raw_tweets, sb)
    save_picks(top3, message_ids, sb)
    print("  Saved.")

    print("Done.")


def _load_multipliers(supabase_client) -> dict[str, float]:
    """Returns {handle: authority_multiplier} for all tracked accounts."""
    rows = supabase_client.table("account_feedback").select("handle,authority_multiplier").execute()
    return {r["handle"]: r["authority_multiplier"] for r in (rows.data or [])}


def _parse_age(created_at: str) -> datetime:
    """Parse tweet created_at into an aware UTC datetime. Returns epoch on failure."""
    try:
        if "T" in created_at:
            return datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        dt = datetime.strptime(created_at, "%a %b %d %H:%M:%S +0000 %Y")
        return dt.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return datetime.fromtimestamp(0, tz=timezone.utc)


if __name__ == "__main__":
    main()
