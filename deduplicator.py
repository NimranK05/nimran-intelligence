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
