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
