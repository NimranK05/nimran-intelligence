"""
reweighter.py — updates authority_multiplier for each account in account_feedback.

Run this weekly (e.g. every Sunday at midnight via Railway cron: 0 0 * * 0):
  python reweighter.py

Multiplier formula:
  ratio      = used_count / shown_count   (0.0 → 1.0)
  multiplier = 0.5 + 1.5 * ratio

  ratio = 0.00  →  multiplier = 0.50  (account never used — heavily down-weighted)
  ratio = 0.33  →  multiplier = 1.00  (neutral)
  ratio = 1.00  →  multiplier = 2.00  (account always used — heavily up-weighted)
"""

import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from supabase import create_client


def run() -> None:
    load_dotenv()
    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

    rows = sb.table("account_feedback").select("*").execute().data or []

    if not rows:
        print("No account_feedback rows found. Nothing to reweight.")
        return

    for row in rows:
        shown      = max(row["shown_count"], 1)   # avoid division by zero
        ratio      = row["used_count"] / shown
        multiplier = round(0.5 + 1.5 * ratio, 4)

        sb.table("account_feedback").update(
            {
                "authority_multiplier": multiplier,
                "updated_at":           datetime.now(timezone.utc).isoformat(),
            }
        ).eq("handle", row["handle"]).execute()

        print(
            f"@{row['handle']:20s}  "
            f"shown={row['shown_count']:3d}  used={row['used_count']:3d}  "
            f"ratio={ratio:.2f}  multiplier={multiplier:.2f}"
        )

    print(f"\nReweighted {len(rows)} account(s).")


if __name__ == "__main__":
    run()
