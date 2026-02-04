"""
record_tracker.py
─────────────────
Owns record.json.  Every other module that needs the historical record
calls into this one.  Nothing else should touch the file directly.

record.json schema
──────────────────
{
  "metadata": {
    "strategy":     "NBA Sharp Money – Top 3 Daily",
    "unit_size":    100,
    "start_date":   "2026-02-03",
    "last_updated": "2026-02-03"
  },
  "summary": { "wins": 0, "losses": 0, "total_profit": 0.0, "total_wagered": 0 },
  "days": [
    {
      "date": "2026-02-03",
      "picks": [
        {
          "id": 1,
          "game": "Lakers @ Knicks",
          "market": "Moneyline",
          "side": "Lakers ML",
          "odds": 168,
          "handle_pct": 63,
          "bet_count_pct": 43,
          "differential": 20,
          "result": null          # null | "W" | "L"
        }
      ]
    }
  ]
}
"""

import json, os
from datetime import date

RECORD_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "record.json")
UNIT_SIZE   = 100   # dollars wagered per pick


# ── internal ──────────────────────────────────────────────────────────────
def _load() -> dict:
    if os.path.exists(RECORD_PATH):
        with open(RECORD_PATH) as fh:
            return json.load(fh)
    return {
        "metadata": {
            "strategy":     "NBA Sharp Money – Top 3 Daily",
            "unit_size":    UNIT_SIZE,
            "start_date":   date.today().isoformat(),
            "last_updated": date.today().isoformat(),
        },
        "summary": {"wins": 0, "losses": 0, "total_profit": 0.0, "total_wagered": 0},
        "days":    [],
    }


def _save(ledger: dict) -> None:
    with open(RECORD_PATH, "w") as fh:
        json.dump(ledger, fh, indent=2)


def _recalc_summary(ledger: dict) -> dict:
    """Walk every graded pick and rebuild summary from scratch."""
    wins = losses = 0
    profit = 0.0
    wagered = 0
    for day in ledger["days"]:
        for p in day["picks"]:
            if p["result"] not in ("W", "L"):
                continue
            wagered += UNIT_SIZE
            if p["result"] == "W":
                wins   += 1
                # American positive odds payout: stake × (odds / 100)
                profit += UNIT_SIZE * (p["odds"] / 100)
            else:
                losses += 1
                profit -= UNIT_SIZE
    return {"wins": wins, "losses": losses,
            "total_profit": round(profit, 2), "total_wagered": wagered}


# ── public API ────────────────────────────────────────────────────────────
def add_day(picks: list[dict]) -> None:
    """Append today's picks (all result=None).  Idempotent within one day."""
    ledger = _load()
    today  = date.today().isoformat()
    if ledger["days"] and ledger["days"][-1]["date"] == today:
        print("[record_tracker] Today already recorded — skipping.")
        return
    ledger["days"].append({
        "date": today,
        "picks": [
            {
                "id":            i + 1,
                "game":          p["game"],
                "market":        p["market"],
                "side":          p["side"],
                "odds":          p["odds"],
                "handle_pct":    p["handle_pct"],
                "bet_count_pct": p["bet_count_pct"],
                "differential":  p["differential"],
                "result":        None,
            }
            for i, p in enumerate(picks)
        ],
    })
    ledger["metadata"]["last_updated"] = today
    _save(ledger)


def update_results(target_date: str, results: list) -> None:
    """
    Grade picks for *target_date*.
    results – list aligned to picks order; each element is "W", "L", or None
              (None = leave untouched).
    """
    ledger = _load()
    for day in ledger["days"]:
        if day["date"] == target_date:
            for pick, outcome in zip(day["picks"], results):
                if outcome is not None:
                    pick["result"] = outcome
            break
    else:
        raise ValueError(f"No record entry for {target_date}")
    ledger["summary"]            = _recalc_summary(ledger)
    ledger["metadata"]["last_updated"] = date.today().isoformat()
    _save(ledger)


def get_summary() -> dict:
    return _load()["summary"]


def get_pending_days() -> list[dict]:
    """Return day-dicts that still have at least one result == None."""
    return [d for d in _load()["days"] if any(p["result"] is None for p in d["picks"])]


def get_monthly_summary() -> dict:
    """
    Return summary stats for the most recently completed month.
    Called on the 1st of each month to generate recap post.
    
    Returns dict with: month_picks, month_wins, month_losses, month_profit,
                      overall_wins, overall_losses, overall_profit
    """
    from datetime import timedelta
    
    ledger = _load()
    today = date.today()
    
    # Last month's date range
    first_of_this_month = today.replace(day=1)
    last_month_end = first_of_this_month - timedelta(days=1)
    last_month_start = last_month_end.replace(day=1)
    
    # Collect last month's picks
    month_wins = month_losses = 0
    month_profit = 0.0
    month_picks = 0
    
    for day in ledger["days"]:
        day_date = date.fromisoformat(day["date"])
        if last_month_start <= day_date <= last_month_end:
            for pick in day["picks"]:
                if pick["result"] in ("W", "L"):
                    month_picks += 1
                    if pick["result"] == "W":
                        month_wins += 1
                        month_profit += UNIT_SIZE * (pick["odds"] / 100)
                    else:
                        month_losses += 1
                        month_profit -= UNIT_SIZE
    
    summary = ledger["summary"]
    
    return {
        "month_picks": month_picks,
        "month_wins": month_wins,
        "month_losses": month_losses,
        "month_profit": round(month_profit, 2),
        "overall_wins": summary["wins"],
        "overall_losses": summary["losses"],
        "overall_profit": summary["total_profit"],
    }
