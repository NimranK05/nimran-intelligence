import math
from datetime import datetime, timezone, timedelta

import numpy as np

NICHE_KEYWORDS_DEFAULT = ["AI", "LLM", "agent", "GPT", "model", "prompt"]

# Normalisation ceilings (adjust if your audience differs)
MAX_ENGAGEMENT = 5000.0    # retweets*2 + likes ceiling
MAX_FOLLOWERS  = 500_000.0  # followers ceiling for log normalisation


def score_tweets(tweets: list[dict], niche_keywords: list[str] = None) -> list[dict]:
    """
    Returns the input tweets enriched with score, velocity_raw, authority_raw.
    """
    keywords = niche_keywords or NICHE_KEYWORDS_DEFAULT
    result = []
    for t in tweets:
        v = _velocity(t)
        a = _authority(t)
        ti = _timing(t)
        r = _replyability(t)
        n = _niche_fit(t, keywords)
        score = v * 0.35 + a * 0.25 + ti * 0.15 + r * 0.15 + n * 0.10
        result.append({**t, "score": round(score, 4), "velocity_raw": v, "authority_raw": a})
    return result


def softmax_rank(scored_tweets: list[dict], top_n: int = 3) -> list[dict]:
    """
    Applies softmax over scores, returns top_n tweets sorted descending by score.
    """
    if not scored_tweets:
        return []
    scores = np.array([t["score"] for t in scored_tweets], dtype=float)
    e = np.exp(scores - scores.max())
    softmax_scores = e / e.sum()
    ranked = sorted(
        zip(softmax_scores, scored_tweets),
        key=lambda x: x[0],
        reverse=True,
    )
    return [t for _, t in ranked[:top_n]]


def assign_pillars(top3: list[dict]) -> list[dict]:
    """
    Tags each tweet with a pillar: Breakdown (highest velocity),
    Stack (highest authority), Leverage (rest).
    """
    if not top3:
        return top3

    breakdown_idx = max(range(len(top3)), key=lambda i: top3[i]["velocity_raw"])
    remaining = [i for i in range(len(top3)) if i != breakdown_idx]
    stack_idx = max(remaining, key=lambda i: top3[i]["authority_raw"]) if remaining else None

    for i, tweet in enumerate(top3):
        if i == breakdown_idx:
            tweet["pillar"] = "Breakdown"
        elif i == stack_idx:
            tweet["pillar"] = "Stack"
        else:
            tweet["pillar"] = "Leverage"

    return top3


# --- sub-scorers ---

def _velocity(t: dict) -> float:
    eng = t["retweets"] * 2 + t["likes"]
    return min(eng / MAX_ENGAGEMENT, 1.0)


def _authority(t: dict) -> float:
    score = math.log10(t["followers"] + 1) / math.log10(MAX_FOLLOWERS + 1)
    if t.get("verified"):
        score += 0.1
    return min(score, 1.0)


def _timing(t: dict) -> float:
    try:
        created = datetime.strptime(t["created_at"], "%a %b %d %H:%M:%S +0000 %Y")
        created = created.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return 0.0
    age = datetime.now(timezone.utc) - created
    if age <= timedelta(hours=6):
        return 1.0
    if age <= timedelta(hours=24):
        return 0.5
    return 0.0


def _replyability(t: dict) -> float:
    text = t.get("text", "")
    if text.endswith("?"):
        return 1.0
    if "?" in text:
        return 0.5
    return 0.0


def _niche_fit(t: dict, keywords: list[str]) -> float:
    text_lower = t.get("text", "").lower()
    for kw in keywords:
        if kw.lower() in text_lower:
            return 1.0
    return 0.0
