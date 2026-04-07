"""
feedback_reader.py — reads ✅/❌ reactions from Discord and logs them to Supabase.

Run this on a schedule (e.g. daily, a few hours after the morning picks land):
  python feedback_reader.py

Requires two extra env vars beyond the core system:
  DISCORD_BOT_TOKEN  — from discord.com/developers (Bot section)
  DISCORD_CHANNEL_ID — right-click #tweet-picks → Copy Channel ID
"""

import os
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv
from supabase import create_client

DISCORD_API  = "https://discord.com/api/v10"
CHECK_EMOJI  = "%E2%9C%85"   # ✅
CROSS_EMOJI  = "%E2%9D%8C"   # ❌


def run() -> None:
    load_dotenv()
    bot_token  = os.environ["DISCORD_BOT_TOKEN"]
    channel_id = os.environ["DISCORD_CHANNEL_ID"]
    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])
    headers = {"Authorization": f"Bot {bot_token}"}

    # Picks that have a Discord message ID
    picks_resp = (
        sb.table("tweet_picks")
        .select("tweet_url,author,discord_message_id")
        .not_.is_("discord_message_id", "null")
        .execute()
    )
    picks = picks_resp.data or []

    # Already-logged message IDs — skip these
    logged_resp = sb.table("pick_feedback").select("discord_message_id").execute()
    logged_ids  = {r["discord_message_id"] for r in (logged_resp.data or [])}

    processed = 0
    for pick in picks:
        mid = pick["discord_message_id"]
        if mid in logged_ids:
            continue

        used       = _has_reaction(headers, channel_id, mid, CHECK_EMOJI)
        not_useful = _has_reaction(headers, channel_id, mid, CROSS_EMOJI)

        if not used and not not_useful:
            continue  # no reaction yet — nothing to log

        verdict = used  # True = used, False = not useful

        # Log the pick verdict
        sb.table("pick_feedback").insert(
            {
                "tweet_url":          pick["tweet_url"],
                "discord_message_id": mid,
                "used":               verdict,
                "logged_at":          datetime.now(timezone.utc).isoformat(),
            }
        ).execute()

        # Increment used_count on the author if the pick was used
        handle = pick.get("author", "")
        if handle and verdict:
            _increment_used(handle, sb)

        label = "✅ Used" if verdict else "❌ Not useful"
        print(f"Logged: @{handle or '?'} — {label}")
        processed += 1

    print(f"Done. {processed} new reaction(s) logged.")


def _has_reaction(headers: dict, channel_id: str, message_id: str, emoji: str) -> bool:
    """Returns True if the message has at least one reaction with the given emoji."""
    url  = f"{DISCORD_API}/channels/{channel_id}/messages/{message_id}/reactions/{emoji}"
    resp = requests.get(url, headers=headers, timeout=10)
    if resp.status_code == 200:
        return len(resp.json()) > 0
    return False


def _increment_used(handle: str, supabase_client) -> None:
    existing = (
        supabase_client.table("account_feedback")
        .select("used_count")
        .eq("handle", handle)
        .execute()
    )
    if existing.data:
        new_count = existing.data[0]["used_count"] + 1
        supabase_client.table("account_feedback").update(
            {"used_count": new_count, "updated_at": datetime.now(timezone.utc).isoformat()}
        ).eq("handle", handle).execute()


if __name__ == "__main__":
    run()
