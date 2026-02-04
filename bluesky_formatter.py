"""
bluesky_formatter.py
────────────────────
Formats posts and bio for Bluesky with:
  - Variable pick counts (not limited to 3)
  - Strategy summary in bio
  - Monthly summary posts
"""

from datetime import date


# ── daily picks post ──────────────────────────────────────────────────────
# Budget: ~290 chars (Bluesky limit is 300)
HEADER_FMT = "🏀 NBA Sharp Money – {date}\n{count} picks meet 20%+ threshold\n\n"
PICK_FMT   = "{n}. {side} ({odds:+d})\n   {h}% handle | {b}% bets | +{diff}% edge\n"
FOOTER     = "⚠️ Entertainment only"


def build_picks_post(picks: list[dict]) -> str:
    """Build daily picks post. Returns empty string if no picks."""
    if not picks:
        return ""
    
    count_label = f"{len(picks)}" if len(picks) > 1 else "1"
    header = HEADER_FMT.format(
        date=date.today().strftime("%b %d"),
        count=count_label
    )
    
    body = ""
    for i, p in enumerate(picks, 1):
        body += PICK_FMT.format(
            n=i, side=p["side"], odds=int(p["odds"]),
            h=p["handle_pct"], b=p["bet_count_pct"], diff=p["differential"]
        )
    
    full = header + body + FOOTER
    
    # Hard cap at 300
    if len(full) > 300:
        # Try removing footer
        full = header + body
        if len(full) > 300:
            # Truncate picks
            full = full[:297] + "..."
    
    return full


# ── monthly summary post ──────────────────────────────────────────────────
def build_monthly_summary(month_name: str, summary: dict) -> str:
    """
    Build end-of-month recap post.
    
    summary should contain:
      month_picks, month_wins, month_losses, month_profit,
      overall_wins, overall_losses, overall_profit
    """
    template = (
        "📊 {month} Recap\n\n"
        "Monthly: {mw}-{ml} ({mwr:.1f}%) | ${mp:+,.0f}\n"
        "Overall: {ow}-{ol} ({owr:.1f}%) | ${op:+,.0f}\n\n"
        "20%+ differential threshold\n"
        "Entertainment only"
    )
    
    mp = summary["month_picks"]
    mw = summary["month_wins"]
    ml = summary["month_losses"]
    mwr = (mw / mp * 100) if mp > 0 else 0
    
    op_total = summary["overall_wins"] + summary["overall_losses"]
    owr = (summary["overall_wins"] / op_total * 100) if op_total > 0 else 0
    
    return template.format(
        month=month_name,
        mw=mw, ml=ml, mwr=mwr, mp=summary["month_profit"],
        ow=summary["overall_wins"], ol=summary["overall_losses"],
        owr=owr, op=summary["overall_profit"]
    )


# ── profile bio ───────────────────────────────────────────────────────────
BIO_TEMPLATE = (
    "🔥 NBA Sharp Money Bot\n"
    "{record} | ${pnl:+,.0f}\n"
    "20%+ differential only\n"
    "Live tracking since {start}"
)


def build_bio(summary: dict, start_date: str) -> str:
    """
    Enhanced bio with strategy summary.
    
    summary: {wins, losses, total_profit, total_wagered}
    start_date: ISO format "2026-02-04"
    """
    w = summary["wins"]
    l = summary["losses"]
    total = w + l
    
    if total == 0:
        record = "0-0"
    else:
        pct = w / total * 100
        record = f"{w}-{l} ({pct:.1f}%)"
    
    # Format start date as "Feb 2026"
    try:
        dt = date.fromisoformat(start_date)
        start_fmt = dt.strftime("%b %Y")
    except:
        start_fmt = start_date
    
    text = BIO_TEMPLATE.format(
        record=record,
        pnl=summary["total_profit"],
        start=start_fmt
    )
    
    return text[:256]  # Bluesky hard limit
