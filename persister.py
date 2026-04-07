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
            "likes":         t.get("likes", 0),
            "bookmarks":     t.get("bookmarks", 0),
            "views":         t.get("views", 0),
        }
        for t in top3
    ]
    supabase_client.table("tweet_picks").insert(rows).execute()
