from unittest.mock import MagicMock
from persister import save_seen_tweets, save_picks

TWEETS = [
    {"id": "1", "text": "a", "author": "u1", "url": ""},
    {"id": "2", "text": "b", "author": "u2", "url": ""},
]
TOP3 = [
    {
        "id": "1", "text": "a", "author": "u1", "url": "https://t.co/1",
        "score": 0.85, "pillar": "Breakdown",
        "velocity_raw": 0.9, "authority_raw": 0.7,
    }
]


def test_save_seen_tweets_upserts_all_ids():
    mock_client = MagicMock()
    mock_client.table.return_value.upsert.return_value.execute.return_value = MagicMock()

    save_seen_tweets(TWEETS, mock_client)

    mock_client.table.assert_called_with("seen_tweets")
    call_args = mock_client.table.return_value.upsert.call_args[0][0]
    ids = [row["tweet_id"] for row in call_args]
    assert set(ids) == {"1", "2"}


def test_save_seen_tweets_deduplicates_ids():
    mock_client = MagicMock()
    mock_client.table.return_value.upsert.return_value.execute.return_value = MagicMock()

    duplicate_tweets = [
        {"id": "1", "text": "a"},
        {"id": "1", "text": "a duplicate"},  # same ID
        {"id": "2", "text": "b"},
    ]
    save_seen_tweets(duplicate_tweets, mock_client)

    call_args = mock_client.table.return_value.upsert.call_args[0][0]
    ids = [row["tweet_id"] for row in call_args]
    assert ids.count("1") == 1  # deduplicated
    assert set(ids) == {"1", "2"}


def test_save_picks_inserts_top3():
    mock_client = MagicMock()
    mock_client.table.return_value.insert.return_value.execute.return_value = MagicMock()

    save_picks(TOP3, mock_client)

    mock_client.table.assert_called_with("tweet_picks")
    call_args = mock_client.table.return_value.insert.call_args[0][0]
    assert len(call_args) == 1
    assert call_args[0]["tweet_id"] == "1"
    assert call_args[0]["pillar"] == "Breakdown"
    assert call_args[0]["score"] == 0.85
