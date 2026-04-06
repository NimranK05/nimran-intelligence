from unittest.mock import MagicMock
from deduplicator import filter_seen

TWEETS = [
    {"id": "1", "text": "a"},
    {"id": "2", "text": "b"},
    {"id": "3", "text": "c"},
]


def test_filter_seen_removes_known_ids():
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.in_.return_value.execute.return_value.data = [
        {"tweet_id": "1"},
        {"tweet_id": "3"},
    ]

    result = filter_seen(TWEETS, mock_client)

    assert len(result) == 1
    assert result[0]["id"] == "2"


def test_filter_seen_returns_all_when_none_seen():
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.in_.return_value.execute.return_value.data = []

    result = filter_seen(TWEETS, mock_client)

    assert len(result) == 3


def test_filter_seen_returns_empty_when_all_seen():
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.in_.return_value.execute.return_value.data = [
        {"tweet_id": "1"},
        {"tweet_id": "2"},
        {"tweet_id": "3"},
    ]

    result = filter_seen(TWEETS, mock_client)

    assert result == []
