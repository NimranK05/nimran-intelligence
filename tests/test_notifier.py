from unittest.mock import patch, MagicMock
from notifier import post_to_discord

TOP3 = [
    {
        "id": "1", "text": "AI agents are taking over!", "author": "karpathy",
        "url": "https://twitter.com/karpathy/status/1",
        "score": 0.8712, "pillar": "Breakdown",
        "velocity_raw": 0.91, "authority_raw": 0.75,
    },
    {
        "id": "2", "text": "LLMs are just autocomplete", "author": "sama",
        "url": "https://twitter.com/sama/status/2",
        "score": 0.7203, "pillar": "Stack",
        "velocity_raw": 0.55, "authority_raw": 0.88,
    },
    {
        "id": "3", "text": "What prompt do you use daily?", "author": "levelsio",
        "url": "https://twitter.com/levelsio/status/3",
        "score": 0.6541, "pillar": "Leverage",
        "velocity_raw": 0.40, "authority_raw": 0.50,
    },
]


def test_post_to_discord_calls_webhook(mocker):
    mock_post = mocker.patch("notifier.requests.post")
    mock_post.return_value.status_code = 204

    post_to_discord(TOP3, webhook_url="https://discord.com/api/webhooks/fake")

    assert mock_post.called
    args, kwargs = mock_post.call_args
    payload = kwargs["json"]
    assert "embeds" in payload
    assert len(payload["embeds"]) == 3


def test_post_to_discord_embed_contains_required_fields(mocker):
    mock_post = mocker.patch("notifier.requests.post")
    mock_post.return_value.status_code = 204

    post_to_discord(TOP3, webhook_url="https://discord.com/api/webhooks/fake")

    payload = mock_post.call_args[1]["json"]
    first_embed = payload["embeds"][0]

    assert "Breakdown" in first_embed["title"]
    assert "karpathy" in first_embed["description"]
    assert "0.87" in first_embed["description"] or "87" in first_embed["description"]
    # velocity and authority shown
    assert any("Velocity" in str(f) for f in first_embed["fields"])
    assert any("Authority" in str(f) for f in first_embed["fields"])


def test_post_to_discord_raises_on_failure(mocker):
    mock_post = mocker.patch("notifier.requests.post")
    mock_post.return_value.status_code = 400
    mock_post.return_value.text = "Bad Request"

    import pytest
    with pytest.raises(RuntimeError, match="Discord webhook failed"):
        post_to_discord(TOP3, webhook_url="https://discord.com/api/webhooks/fake")
