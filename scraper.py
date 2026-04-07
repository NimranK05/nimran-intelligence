from apify_client import ApifyClient


# kaitoeasyapi/twitter-x-data-tweet-scraper-pay-per-result-cheapest:
# - $0.00025/tweet (cheapest viable option, half the price of gentle_cloud)
# - 34.7M runs — most battle-tested after apidojo
# - Supports queryType='Top': returns genuinely viral tweets, not just recent ones
# - Returns bookmarkCount + viewCount: strong engagement signals for scoring
# - Works on Apify Free Plan ($5/month); ~$0.30/month at 2 runs/day
ACTOR_ID = "kaitoeasyapi/twitter-x-data-tweet-scraper-pay-per-result-cheapest"


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
        retweets, likes, bookmarks, views, created_at, url
    """
    client = ApifyClient(api_token)

    # Build search terms: main keyword query + per-account queries
    # kaitoeasyapi processes each searchTerm separately — accounts guaranteed coverage
    keyword_query = keywords[0] if len(keywords) == 1 else " OR ".join(keywords)
    account_queries = [f"from:{handle} lang:en" for handle in accounts]
    search_terms = [keyword_query] + account_queries

    per_term = max(1, -(-max_items // len(search_terms)))  # ceiling division

    run_input = {
        "searchTerms": search_terms,
        "maxItems": per_term,  # actor applies this per search term, so divide by term count
        "queryType": "Top",               # return top-performing tweets, not just latest
        "min_faves": 50,                  # minimum 50 likes — filters out noise at source
        "include:nativeretweets": False,  # original content only
        "filter:replies": False,          # no reply chains
    }

    run = client.actor(ACTOR_ID).call(run_input=run_input)
    if run is None:
        raise RuntimeError(f"Apify actor {ACTOR_ID} failed to start or timed out")

    dataset_id = run.get("defaultDatasetId")
    # Hard slice as a safety net in case the actor overshoots
    items = client.dataset(dataset_id).list_items(limit=max_items).items[:max_items]

    tweets = []
    for item in items:
        normalised = _normalise(item)
        if normalised is not None:
            tweets.append(normalised)

    return tweets


def _normalise(raw: dict) -> dict | None:
    tweet_id = raw.get("id")
    if not tweet_id:
        return None

    author = raw.get("author", {})

    return {
        "id": str(tweet_id),
        "text": raw.get("text", ""),
        "author": author.get("userName") or "",
        "followers": author.get("followers") or 0,
        "verified": author.get("isBlueVerified") or author.get("isVerified") or False,
        "retweets": raw.get("retweetCount") or 0,
        "likes": raw.get("likeCount") or 0,
        "bookmarks": raw.get("bookmarkCount") or 0,
        "views": raw.get("viewCount") or 0,
        "created_at": raw.get("createdAt") or "",
        "url": raw.get("twitterUrl") or raw.get("url") or f"https://x.com/i/status/{tweet_id}",
    }
