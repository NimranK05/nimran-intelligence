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
            f"**@{tweet['author']}** (Score: {score_pct}%)\n\n"
            f"{tweet['text']}\n\n"
            f"[View tweet]({tweet['url']})"
        ),
        "color": PILLAR_COLOURS.get(pillar, 0x95A5A6),
        "fields": [
            {"name": "Velocity", "value": f"{velocity_pct}%", "inline": True},
            {"name": "Authority", "value": f"{authority_pct}%", "inline": True},
            {"name": "Likes", "value": f"{tweet.get('likes', 0):,}", "inline": True},
            {"name": "Bookmarks", "value": f"{tweet.get('bookmarks', 0):,}", "inline": True},
            {"name": "Views", "value": f"{tweet.get('views', 0):,}", "inline": True},
        ],
    }
