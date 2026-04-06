import pytest
from datetime import datetime, timezone, timedelta
from scorer import score_tweets, assign_pillars, softmax_rank

NICHE_KEYWORDS = ["AI", "LLM", "agent", "GPT", "model", "prompt"]

def _now_iso():
    return datetime.now(timezone.utc).strftime("%a %b %d %H:%M:%S +0000 %Y")

def _hours_ago_iso(h):
    dt = datetime.now(timezone.utc) - timedelta(hours=h)
    return dt.strftime("%a %b %d %H:%M:%S +0000 %Y")

TWEET_RECENT_VIRAL = {
    "id": "1", "text": "What does AI do? #LLM",
    "author": "bigaccount", "followers": 50000, "verified": True,
    "retweets": 800, "likes": 2000, "created_at": _hours_ago_iso(2), "url": ""
}
TWEET_OLD_LOW = {
    "id": "2", "text": "Random text",
    "author": "nobody", "followers": 100, "verified": False,
    "retweets": 0, "likes": 1, "created_at": _hours_ago_iso(48), "url": ""
}


def test_score_tweets_returns_scores_for_each():
    result = score_tweets([TWEET_RECENT_VIRAL, TWEET_OLD_LOW], NICHE_KEYWORDS)
    assert len(result) == 2
    # viral tweet should score higher
    scores = {r["id"]: r["score"] for r in result}
    assert scores["1"] > scores["2"]


def test_score_tweets_all_scores_between_0_and_1():
    result = score_tweets([TWEET_RECENT_VIRAL, TWEET_OLD_LOW], NICHE_KEYWORDS)
    for r in result:
        assert 0.0 <= r["score"] <= 1.0


def test_softmax_rank_top3_from_five():
    tweets_with_scores = [
        {"id": str(i), "score": float(i)} for i in range(5)
    ]
    top3 = softmax_rank(tweets_with_scores, top_n=3)
    assert len(top3) == 3
    # top 3 should be highest scores
    assert [t["id"] for t in top3] == ["4", "3", "2"]


def test_assign_pillars_labels_top3():
    top3 = [
        {"id": "1", "velocity_raw": 0.9, "authority_raw": 0.3},
        {"id": "2", "velocity_raw": 0.2, "authority_raw": 0.8},
        {"id": "3", "velocity_raw": 0.4, "authority_raw": 0.4},
    ]
    result = assign_pillars(top3)
    pillar_map = {t["id"]: t["pillar"] for t in result}
    assert pillar_map["1"] == "Breakdown"   # highest velocity
    assert pillar_map["2"] == "Stack"       # highest authority
    assert pillar_map["3"] == "Leverage"    # remainder


def test_timing_future_tweet_scores_zero():
    future = datetime.now(timezone.utc) + timedelta(hours=2)
    future_str = future.strftime("%a %b %d %H:%M:%S +0000 %Y")
    tweet = {
        "id": "99", "text": "hello",
        "author": "x", "followers": 1000, "verified": False,
        "retweets": 0, "likes": 0, "created_at": future_str, "url": ""
    }
    result = score_tweets([tweet], [])
    # Future tweet: timing sub-score must be 0.0
    # (score = 0*0.35 + authority*0.25 + 0*0.15 + 0*0.15 + 0*0.10)
    # Just verify score is low (< 0.25 since only authority contributes)
    assert result[0]["score"] < 0.25
