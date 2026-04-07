from datetime import datetime, timezone


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def save_seen_tweets(tweets: list[dict], supabase_client) -> None:
    """
    Upserts all tweet IDs into seen_tweets so they are skipped next run.
    """
    if not tweets:
        return
    seen = set()
    rows = []
    for t in tweets:
        if t["id"] not in seen:
            seen.add(t["id"])
            rows.append({"tweet_id": t["id"]})
    supabase_client.table("seen_tweets").upsert(rows).execute()


def save_picks(top3: list[dict], message_ids: list[dict], supabase_client) -> None:
    """
    Inserts the top-3 picks into tweet_picks and increments shown_count in
    account_feedback for each author.

    message_ids is the list returned by post_to_discord:
      [{"tweet_url": ..., "discord_message_id": ...}, ...]
    """
    if not top3:
        return

    id_map = {m["tweet_url"]: m["discord_message_id"] for m in message_ids}

    rows = [
        {
            "tweet_id":           t["id"],
            "tweet_url":          t.get("url", ""),
            "author":             t.get("author", ""),
            "text":               t.get("text", ""),
            "score":              t["score"],
            "pillar":             t.get("pillar", ""),
            "velocity_raw":       t["velocity_raw"],
            "authority_raw":      t["authority_raw"],
            "likes":              t.get("likes", 0),
            "bookmarks":          t.get("bookmarks", 0),
            "views":              t.get("views", 0),
            "discord_message_id": id_map.get(t.get("url", "")),
        }
        for t in top3
    ]
    supabase_client.table("tweet_picks").insert(rows).execute()

    for t in top3:
        handle = t.get("author", "")
        if not handle:
            continue
        _increment_shown(handle, supabase_client)


def _increment_shown(handle: str, supabase_client) -> None:
    existing = (
        supabase_client.table("account_feedback")
        .select("shown_count")
        .eq("handle", handle)
        .execute()
    )
    if existing.data:
        new_count = existing.data[0]["shown_count"] + 1
        supabase_client.table("account_feedback").update(
            {"shown_count": new_count, "updated_at": _now()}
        ).eq("handle", handle).execute()
    else:
        supabase_client.table("account_feedback").insert(
            {
                "handle":               handle,
                "shown_count":          1,
                "used_count":           0,
                "authority_multiplier": 1.0,
                "updated_at":           _now(),
            }
        ).execute()
