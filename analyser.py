"""
analyser.py
───────────
Sharp Money formula with 20% minimum differential threshold.
Returns ALL qualifying picks (not limited to top 3).
"""

from data_fetcher import fetch_odds, fetch_splits

MIN_DIFFERENTIAL = 20          # 20% threshold - configurable


def analyse() -> list[dict]:
    """
    Return all picks meeting the 20% differential threshold.
    Could be 0, could be 10+ depending on market conditions.
    """
    odds   = fetch_odds()
    splits = fetch_splits()

    if not splits:
        print("[analyser] No splits data — cannot select picks today.")
        return []

    # Merge odds + splits
    candidates = []
    for row in odds:
        key = (row["game"], row["market"], row["side"])
        if key not in splits:
            continue
        h = splits[key]["handle_pct"]
        b = splits[key]["bet_count_pct"]
        if b == 0:
            continue

        diff  = h - b
        ratio = round(h / b, 2)
        score = round(abs(diff) * ratio, 2)

        if diff >= MIN_DIFFERENTIAL:            # Only sharp-side picks
            candidates.append(dict(
                game=row["game"],
                market=row["market"],
                side=row["side"],
                odds=row["odds"],
                handle_pct=h,
                bet_count_pct=b,
                differential=diff,
                avg_bet_size_ratio=ratio,
                priority_score=score,
            ))

    # Sort by differential (highest edge first)
    candidates.sort(key=lambda c: (c["differential"], c["priority_score"]), reverse=True)
    
    if not candidates:
        print(f"[analyser] No picks cleared the {MIN_DIFFERENTIAL}% threshold today.")
    else:
        print(f"[analyser] {len(candidates)} picks meet threshold.")
    
    return candidates
