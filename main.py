#!/usr/bin/env python3
"""
main.py
───────
Daily orchestrator with:
  - Conditional posting (skip if no qualifying picks)
  - Monthly summary on 1st of month
  - Real performance tracking from day 1
"""

import sys, os, json, base64, requests
from datetime import date, datetime
from dotenv import load_dotenv

load_dotenv()

from result_resolver    import resolve_pending
from analyser           import analyse
from record_tracker     import add_day, get_summary, get_monthly_summary, _load
from bluesky_formatter  import build_picks_post, build_bio, build_monthly_summary
from bluesky_poster     import post_skeet, update_profile


# ── GitHub commit ─────────────────────────────────────────────────────────
def _commit_record():
    """Push record.json to repo via GitHub API."""
    token = os.getenv("GITHUB_TOKEN")
    repo  = os.getenv("GITHUB_REPO")
    if not token or not repo:
        print("[main] Skipping commit – GITHUB_TOKEN/GITHUB_REPO not set.")
        return

    path    = "record.json"
    api_url = f"https://api.github.com/repos/{repo}/contents/{path}"
    headers = {"Authorization": f"token {token}",
               "Accept": "application/vnd.github.v3+json"}

    head = requests.get(api_url, headers=headers, timeout=15)
    sha  = head.json().get("sha") if head.status_code == 200 else None

    record_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), path)
    with open(record_path, "rb") as fh:
        content = base64.b64encode(fh.read()).decode()

    payload = {"message": "chore: update record.json", "content": content}
    if sha:
        payload["sha"] = sha

    resp = (requests.put if sha else requests.post)(
        api_url, headers=headers, json=payload, timeout=15)
    resp.raise_for_status()
    print("[main] record.json committed to GitHub.")


# ── main ──────────────────────────────────────────────────────────────────
def main():
    print("=" * 68)
    print("  SHARP MONEY BOT – Bluesky Edition (20% Threshold)")
    print("=" * 68)

    # 1 – grade yesterday
    print("\n[1/6] Resolving pending results …")
    try:
        resolve_pending()
    except Exception as exc:
        print(f"[1/6] WARNING (non-fatal): {exc}")

    # 2 – check if monthly summary needed
    print("\n[2/6] Checking for monthly summary …")
    today = date.today()
    if today.day == 1:
        # Post monthly recap
        try:
            month_summary = get_monthly_summary()
            if month_summary and month_summary.get("month_picks", 0) > 0:
                month_name = (today.replace(day=1) - datetime.timedelta(days=1)).strftime("%B")
                summary_post = build_monthly_summary(month_name, month_summary)
                print(f"[main] Posting {month_name} summary …")
                post_skeet(summary_post)
        except Exception as exc:
            print(f"[main] Monthly summary failed (non-fatal): {exc}")

    # 3 – analyse today
    print("\n[3/6] Analysing today's markets …")
    picks = analyse()
    
    if not picks:
        print("[main] No picks meet 20% threshold today. Skipping post.")
        # Update bio even on quiet days
        try:
            ledger = _load()
            start_date = ledger["metadata"].get("start_date", today.isoformat())
            bio = build_bio(get_summary(), start_date)
            update_profile(bio)
        except:
            pass
        sys.exit(0)  # Clean exit – not an error
    
    print(f"[main] {len(picks)} picks selected:")
    for i, p in enumerate(picks, 1):
        print(f"       {i}. {p['side']}  diff=+{p['differential']}%  odds={p['odds']:+d}")

    # 4 – persist
    print("\n[4/6] Persisting picks …")
    add_day(picks)

    # 5 – format
    print("\n[5/6] Formatting post + bio …")
    post_text = build_picks_post(picks)
    ledger = _load()
    start_date = ledger["metadata"].get("start_date", today.isoformat())
    bio_text = build_bio(get_summary(), start_date)
    
    print(f"  Post ({len(post_text)} chars):\n{post_text}")
    print(f"\n  Bio ({len(bio_text)} chars):\n{bio_text}")

    # 6 – post
    print("\n[6/6] Posting to Bluesky …")
    if not post_skeet(post_text):
        print("[main] FATAL – post not created.")
        sys.exit(1)
    update_profile(bio_text)

    # 7 – commit
    print("\n[commit] Pushing record …")
    try:
        _commit_record()
    except Exception as exc:
        print(f"[commit] WARNING: {exc}")

    print("\n" + "=" * 68)
    print("  Done.")
    print("=" * 68)


if __name__ == "__main__":
    main()
