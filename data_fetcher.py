"""
data_fetcher.py  v2  –  free scraper edition
────────────────────────────────────────────
  fetch_odds()   –  live lines via The Odds API (free tier, 500 req/mo)
  fetch_splits() –  handle% + bet-count% scraped from free websites

Primary splits source
─────────────────────
DraftKings Network  –  dknetwork.draftkings.com/draftkings-sportsbook-betting-splits/
  • Shows BOTH Bets % and Handle % for Spread, Total, and Moneyline
  • Data is server-rendered in the HTML (no headless browser needed)
  • Updates live; we hit it once per day in the nightly CI run
  • Completely free, no account required

Fallback sources (tried in order if DK Network fails)
─────────────────────────────────────────────────────
  • ScoresAndOdds  –  scoresandodds.com/nba/consensus-picks
  • OddsShark      –  oddsshark.com/nba/consensus-picks
Both embed a __NEXT_DATA__ JSON hydration payload; we parse that.

Rate / legal note
─────────────────
One request per source per day, inside the nightly GitHub Actions run.
"""

import os, re, json, requests
from dotenv import load_dotenv
load_dotenv()

ODDS_API_KEY = os.getenv("ODDS_API_KEY", "YOUR_ODDS_API_KEY_HERE")
BASE         = "https://api.the-odds-api.com/v4"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
}


# ══════════════════════════════════════════════════════════════════════
# 1.  ODDS  –  The Odds API
# ══════════════════════════════════════════════════════════════════════
def fetch_odds() -> list[dict]:
    """Return one dict per tradeable outcome today."""
    url = f"{BASE}/sports/basketball_nba/odds/"
    params = dict(apiKey=ODDS_API_KEY, regions="us",
                  markets="h2h,spreads,totals", oddsFormat="american")
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()

    rows = []
    for game in resp.json():
        home, away = game["home_team"], game["away_team"]
        label = f"{away} @ {home}"
        for bm in game.get("bookmakers", [])[:1]:
            for mkt in bm.get("markets", []):
                mkey  = mkt["key"]
                mtype = {"h2h": "Moneyline", "spreads": "Spread",
                         "totals": "Total"}.get(mkey)
                if not mtype:
                    continue
                for o in mkt.get("outcomes", []):
                    name, price, pt = o["name"], o["price"], o.get("point")
                    if   mtype == "Spread":  side = f"{name} {pt:+.1f}"
                    elif mtype == "Total":   side = f"{name} {pt}"
                    else:                    side = f"{name} ML"
                    rows.append(dict(game=label, market=mtype, side=side,
                                     odds=price, home_team=home, away_team=away))
    return rows


# ══════════════════════════════════════════════════════════════════════
# 2.  SPLITS  –  scrapers
# ══════════════════════════════════════════════════════════════════════

# ── Source A: DraftKings Network (primary) ────────────────────────────
# The page renders each game as a series of market blocks.  After
# stripping tags the text follows a predictable line-by-line pattern
# that we walk sequentially, tracking game + market context as we go.

DK_URL = ("https://dknetwork.draftkings.com/"
          "draftkings-sportsbook-betting-splits/"
          "?tb_eg=88808&tb_edate=today&tb_emt=0")   # eg=88808 = NBA


def _scrape_dk() -> dict:
    try:
        resp = requests.get(DK_URL, headers=HEADERS, timeout=25)
        resp.raise_for_status()
    except Exception as exc:
        print(f"[fetcher] DK Network request failed: {exc}")
        return {}

    # strip HTML tags → plain text, then parse
    text = re.sub(r'<[^>]+>', '\n', resp.text)
    return _parse_dk_text(text)


def _parse_dk_text(text: str) -> dict:
    """
    Line-by-line state machine.  State variables:
      game_label  – "Away @ Home"  (set when we see that pattern)
      market      – "Moneyline" | "Spread" | "Total"
      skip_next   – True right after a market header (skip column names)

    A data row is four consecutive lines: side / odds / handle% / bets%.
    We consume all four at once and advance the pointer by 4.
    """
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    splits      = {}
    game_label  = None
    market      = None
    skip_next   = False

    i = 0
    while i < len(lines):
        line = lines[i]

        # ── game separator (##### or similar) ─────────────────────
        if line.startswith("#"):
            game_label = None
            market     = None
            i += 1
            continue

        # ── date/time line ────────────────────────────────────────
        if "," in line and ("PM" in line or "AM" in line) and len(line) < 30:
            i += 1
            continue

        # ── game label ────────────────────────────────────────────
        if " @ " in line and game_label is None and len(line) < 60:
            game_label = line
            i += 1
            continue

        # ── market type ───────────────────────────────────────────
        if line in ("Moneyline", "Spread", "Total"):
            market    = line
            skip_next = True          # column-header row follows
            i += 1
            continue

        # ── column header ("Odds  % Handle  % Bets") ─────────────
        if skip_next:
            skip_next = False
            i += 1
            continue

        # ── data row (4 lines: side / odds / H% / B%) ────────────
        if game_label and market and i + 3 < len(lines):
            side_raw   = lines[i]
            odds_raw   = lines[i + 1]
            handle_raw = lines[i + 2]
            bets_raw   = lines[i + 3]

            if (re.match(r'^[+-]?\d+$', odds_raw) and
                    handle_raw.endswith('%') and bets_raw.endswith('%')):

                handle_pct = int(handle_raw.rstrip('%'))
                bets_pct   = int(bets_raw.rstrip('%'))

                # strip 3-letter sportsbook/team code prefix (e.g. "OKC ")
                side_clean = re.sub(r'^[A-Z]{3}\s+', '', side_raw)

                # label: append " ML" for bare moneyline team names
                if market == "Moneyline" and not re.search(r'[+-]\d', side_clean):
                    side_label = f"{side_clean} ML"
                else:
                    side_label = side_clean

                splits[(game_label, market, side_label)] = {
                    "handle_pct":    handle_pct,
                    "bet_count_pct": bets_pct,
                }
                i += 4
                continue

        i += 1

    return splits


# ── Source B: ScoresAndOdds (fallback) ────────────────────────────────
# Embeds data in <script id="__NEXT_DATA__"> JSON.
def _scrape_sao() -> dict:
    url = "https://www.scoresandodds.com/nba/consensus-picks"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
    except Exception as exc:
        print(f"[fetcher] ScoresAndOdds request failed: {exc}")
        return {}

    match = re.search(
        r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>',
        resp.text, re.DOTALL)
    if not match:
        print("[fetcher] ScoresAndOdds: __NEXT_DATA__ not found.")
        return {}
    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError:
        return {}

    cd = (data.get("props", {})
              .get("pageProps", {})
              .get("consensusData", []))
    if isinstance(cd, dict):
        cd = [cd]

    splits = {}
    for block in cd:
        for game in block.get("games", []):
            splits.update(_parse_next_data_game(game))
    return splits


def _parse_next_data_game(game: dict) -> dict:
    """Extract splits from one game object inside __NEXT_DATA__."""
    away = game.get("away", "")
    home = game.get("home", "")
    if not away or not home:
        return {}
    label = f"{away} @ {home}"

    splits = {}
    # common key patterns
    checks = [
        ("Moneyline", "mlAway",  away),
        ("Moneyline", "mlHome",  home),
        ("Spread",    "spreadAway", away),
        ("Spread",    "spreadHome", home),
        ("Total",     "totalOver",  "Over"),
        ("Total",     "totalUnder", "Under"),
    ]
    for mtype, key, team in checks:
        entry = game.get(key)
        if not isinstance(entry, dict):
            continue
        bets   = entry.get("bets")
        handle = entry.get("handle")
        if bets is None or handle is None:
            continue

        if   mtype == "Moneyline": side = f"{team} ML"
        elif mtype == "Spread":
            pt   = entry.get("point", 0)
            side = f"{team} {pt:+.1f}"
        else:
            pt   = entry.get("point", 0)
            side = f"{team} {pt}"

        splits[(label, mtype, side)] = {
            "handle_pct":    int(handle),
            "bet_count_pct": int(bets),
        }
    return splits


# ── Source C: OddsShark (fallback) ────────────────────────────────────
def _scrape_oddsshark() -> dict:
    url = "https://www.oddsshark.com/nba/consensus-picks"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
    except Exception as exc:
        print(f"[fetcher] OddsShark request failed: {exc}")
        return {}
    # same __NEXT_DATA__ pattern as SAO
    match = re.search(
        r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>',
        resp.text, re.DOTALL)
    if not match:
        return {}
    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError:
        return {}
    cd = (data.get("props", {})
              .get("pageProps", {})
              .get("consensusData", []))
    if isinstance(cd, dict):
        cd = [cd]
    splits = {}
    for block in cd:
        for game in block.get("games", []):
            splits.update(_parse_next_data_game(game))
    return splits


# ══════════════════════════════════════════════════════════════════════
# PUBLIC entry-point
# ══════════════════════════════════════════════════════════════════════
def fetch_splits() -> dict:
    """
    Try DK Network first (best free data), then fall back to SAO and
    OddsShark.  Return the first non-empty result.
    """
    sources = [
        ("DraftKings Network", _scrape_dk),
        ("ScoresAndOdds",      _scrape_sao),
        ("OddsShark",          _scrape_oddsshark),
    ]
    for name, fn in sources:
        print(f"[fetcher] Trying {name} …")
        result = fn()
        if result:
            print(f"[fetcher] {name} returned {len(result)} split entries.")
            return result
        print(f"[fetcher] {name} returned nothing — trying next source.")

    # ── manual override for offline / CI testing ─────────────────
    # Uncomment to force-feed sample data and verify the full pipeline:
    #
    # return {
    #     ("Thunder @ Lakers",  "Moneyline", "Thunder ML"):  {"handle_pct": 63, "bet_count_pct": 43},
    #     ("Jazz @ Nuggets",    "Moneyline", "Jazz ML"):     {"handle_pct": 29, "bet_count_pct": 14},
    #     ("Thunder @ Lakers",  "Spread",    "Thunder +4.5"):{"handle_pct": 52, "bet_count_pct": 39},
    # }

    print("[fetcher] WARNING: all free sources returned empty. "
          "Uncomment the manual override above to test end-to-end.")
    return {}
