"""
result_resolver.py
──────────────────
Grades pending picks by fetching final scores from ESPN's public
scoreboard endpoint (no API key required).

Supported markets
─────────────────
    Moneyline   – fully graded (win / loss)
    Spread      – graded when the pick's odds field is used as a proxy
                  for the spread number (see _grade_spread)
    Total       – not yet graded (requires closing-line total, which we
                  don't currently store).  Left pending with a log note.

ESPN endpoint (public, no auth):
    https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard
"""

import requests
from record_tracker import get_pending_days, update_results

ESPN_URL = ("https://site.api.espn.com/apis/site/v2/"
            "sports/basketball/nba/scoreboard")


# ── ESPN fetch ────────────────────────────────────────────────────────────
def _espn_scores() -> list[dict]:
    resp = requests.get(ESPN_URL, timeout=15)
    resp.raise_for_status()
    out = []
    for evt in resp.json().get("events", []):
        comp = evt.get("competitions", [{}])[0]
        teams = comp.get("competitors", [])
        if len(teams) < 2:
            continue
        # ESPN index 0 = home, 1 = away
        out.append(dict(
            home_team  = teams[0]["team"]["displayName"],
            away_team  = teams[1]["team"]["displayName"],
            home_score = int(teams[0].get("score", 0)),
            away_score = int(teams[1].get("score", 0)),
            is_final   = comp.get("status", {}).get("type", {}).get("id") == "3",
        ))
    return out


# ── matching ──────────────────────────────────────────────────────────────
def _norm(s: str) -> str:
    return s.lower().strip()


def _find_game(pick_game: str, espn_games: list[dict]):
    """Match 'Away @ Home' to an ESPN dict.  Returns None on miss."""
    parts = pick_game.split(" @ ")
    if len(parts) != 2:
        return None
    away, home = _norm(parts[0]), _norm(parts[1])
    for eg in espn_games:
        if _norm(eg["away_team"]) == away and _norm(eg["home_team"]) == home:
            return eg
    return None


# ── grading ───────────────────────────────────────────────────────────────
def _grade(pick: dict, eg: dict):
    """Return 'W', 'L', or None (cannot grade yet)."""
    if not eg["is_final"]:
        return None

    market = pick["market"]
    side   = pick["side"]
    hs, aws = eg["home_score"], eg["away_score"]

    if market == "Moneyline":
        team = side.replace(" ML", "").strip()
        if _norm(team) == _norm(eg["home_team"]):
            return "W" if hs > aws else "L"
        if _norm(team) == _norm(eg["away_team"]):
            return "W" if aws > hs else "L"
        print(f"[resolver] WARNING: cannot match team '{team}'")
        return None

    if market == "Spread":
        # side format: "Lakers -4.5"  – last token is the spread number
        tokens = side.rsplit(" ", 1)
        if len(tokens) != 2:
            return None
        team_name = tokens[0]
        try:
            spread = float(tokens[1])
        except ValueError:
            return None
        # Determine if the team is home or away
        if _norm(team_name) == _norm(eg["home_team"]):
            adjusted = hs - aws - spread
        elif _norm(team_name) == _norm(eg["away_team"]):
            adjusted = aws - hs - spread
        else:
            return None
        if adjusted > 0:
            return "W"
        if adjusted < 0:
            return "L"
        return None                        # push – treated as pending

    if market == "Total":
        # side format: "Over 228.5" or "Under 228.5"
        tokens = side.split(" ", 1)
        if len(tokens) != 2:
            return None
        direction = tokens[0].lower()
        try:
            line = float(tokens[1])
        except ValueError:
            return None
        total = hs + aws
        if direction == "over":
            return "W" if total > line else ("L" if total < line else None)
        if direction == "under":
            return "W" if total < line else ("L" if total > line else None)
        return None

    return None


# ── main ──────────────────────────────────────────────────────────────────
def resolve_pending() -> None:
    pending_days = get_pending_days()
    if not pending_days:
        print("[resolver] Nothing pending.")
        return

    espn = _espn_scores()

    for day in pending_days:
        results = []
        any_new = False
        for pick in day["picks"]:
            if pick["result"] is not None:
                results.append(None)       # already graded; don't overwrite
                continue
            eg = _find_game(pick["game"], espn)
            if eg is None:
                print(f"[resolver] No ESPN match for '{pick['game']}' on {day['date']}")
                results.append(None)
                continue
            grade = _grade(pick, eg)
            if grade:
                print(f"[resolver] {day['date']} | {pick['side']} → {grade}")
                results.append(grade)
                any_new = True
            else:
                results.append(None)

        if any_new:
            update_results(day["date"], results)
