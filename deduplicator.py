# deduplicator.py
import logging

logger = logging.getLogger(__name__)


def filter_seen(tweets: list[dict], supabase_client) -> list[dict]:
    """
    Returns only tweets whose IDs are NOT already in the seen_tweets table.
    On Supabase query failure, logs a warning and returns all tweets (safe degradation).
    """
    if not tweets:
        return []

    ids = [t["id"] for t in tweets]

    try:
        response = (
            supabase_client
            .table("seen_tweets")
            .select("tweet_id")
            .in_("tweet_id", ids)
            .execute()
        )
        seen_ids = {row["tweet_id"] for row in (response.data or [])}
    except Exception:
        logger.warning("seen_tweets query failed; treating all tweets as unseen", exc_info=True)
        seen_ids = set()

    return [t for t in tweets if t["id"] not in seen_ids]
