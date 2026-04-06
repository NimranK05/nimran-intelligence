from unittest.mock import MagicMock
from scraper import fetch_tweets

SEED_KEYWORDS = ["AI agents", "LLM"]
WATCHED_ACCOUNTS = ["sama", "karpathy"]

def test_fetch_tweets_returns_list_of_dicts(mocker):
    mock_dataset = [
        {
            "id": "123",
            "full_text": "Hello world",
            "user": {"screen_name": "testuser", "followers_count": 1000, "verified": False},
            "retweet_count": 5,
            "favorite_count": 20,
            "created_at": "Mon Apr 06 12:00:00 +0000 2026",
            "url": "https://twitter.com/testuser/status/123",
        }
    ]
    mock_client = MagicMock()
    mock_client.actor.return_value.call.return_value = MagicMock(
        get_dataset=MagicMock(return_value=MagicMock(
            iterate_items=MagicMock(return_value=iter(mock_dataset))
        ))
    )
    mocker.patch("scraper.ApifyClient", return_value=mock_client)

    tweets = fetch_tweets(
        api_token="fake-token",
        keywords=SEED_KEYWORDS,
        accounts=WATCHED_ACCOUNTS,
        max_items=50,
    )

    assert isinstance(tweets, list)
    assert len(tweets) == 1
    assert tweets[0]["id"] == "123"
    assert tweets[0]["text"] == "Hello world"
    assert tweets[0]["author"] == "testuser"
    assert tweets[0]["followers"] == 1000
    assert tweets[0]["retweets"] == 5
    assert tweets[0]["likes"] == 20
    assert tweets[0]["url"] == "https://twitter.com/testuser/status/123"


def test_fetch_tweets_limits_to_max_items(mocker):
    raw = [
        {
            "id": str(i),
            "full_text": f"tweet {i}",
            "user": {"screen_name": "u", "followers_count": 100, "verified": False},
            "retweet_count": 0,
            "favorite_count": 0,
            "created_at": "Mon Apr 06 12:00:00 +0000 2026",
            "url": f"https://twitter.com/u/status/{i}",
        }
        for i in range(80)
    ]
    mock_client = MagicMock()
    mock_client.actor.return_value.call.return_value = MagicMock(
        get_dataset=MagicMock(return_value=MagicMock(
            iterate_items=MagicMock(return_value=iter(raw))
        ))
    )
    mocker.patch("scraper.ApifyClient", return_value=mock_client)

    tweets = fetch_tweets("fake-token", ["AI"], [], max_items=50)
    assert len(tweets) == 50
