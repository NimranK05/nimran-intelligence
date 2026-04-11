import requests

PILLAR_COLOURS = {
    "Breakdown": 0xE74C3C,  # red
    "Stack":     0x3498DB,  # blue
    "Leverage":  0x2ECC71,  # green
}


def post_to_discord(top3: list[dict], webhook_url: str) -> list[dict]:
    """
    Posts each tweet as a separate Discord message so reactions can target
    individual picks. Uses ?wait=true to receive the message ID back.

    Returns a list of dicts: [{"tweet_url": ..., "discord_message_id": ...}, ...]
    Raises RuntimeError if any Discord request fails.
    """
    results = []
    for rank, tweet in enumerate(top3, start=1):
        embed = _build_embed(rank, tweet)
        payload = {"username": "Tweet Scout", "embeds": [embed]}
        resp = requests.post(f"{webhook_url}?wait=true", json=payload, timeout=10)
        if not (200 <= resp.status_code < 300):
            raise RuntimeError(f"Discord webhook failed: {resp.status_code} — {resp.text}")
        message_id = resp.json().get("id")
        results.append({"tweet_url": tweet.get("url", ""), "discord_message_id": message_id})
    return results


def _build_embed(rank: int, tweet: dict) -> dict:
    pillar = tweet.get("pillar", "Leverage")
    score_pct = int(tweet["score"] * 100)
    velocity_pct = int(tweet["velocity_raw"] * 100)
    authority_pct = int(tweet["authority_raw"] * 100)

    text = tweet['text']
    if len(text) > 3000:
        text = text[:3000] + "…"

    return {
        "title": f"#{rank} [{pillar}] — Score: {score_pct}%",
        "description": (
            f"**@{tweet['author']}** (Score: {score_pct}%)\n\n"
            f"{text}\n\n"
            f"[View tweet]({tweet['url']})\n\n"
            f"React ✅ if you used this · ❌ if not useful"
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
