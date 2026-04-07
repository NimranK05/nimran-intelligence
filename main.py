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

    print("Saving to Supabase...")
    save_seen_tweets(raw_tweets, sb)   # mark ALL fetched as seen
    save_picks(top3, sb)
    print("  Saved.")

    print("Posting to Discord...")
    post_to_discord(top3, webhook_url)
    print("  Posted.")

    print("Done.")


if __name__ == "__main__":
    main()
