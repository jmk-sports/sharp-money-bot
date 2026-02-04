# Sharp Money Bot - Complete Setup Guide
**Bluesky Edition | 20% Threshold Strategy**

---

## What This Bot Does

✅ **Posts qualifying NBA picks** when handle% - bet count% ≥ 20%  
✅ **Variable volume** — could be 0, 1, or 10+ picks per day  
✅ **Skip days with no qualifiers** — only posts when edge is real  
✅ **Monthly summaries** — auto-posted on 1st of each month  
✅ **Live performance tracking** — starts from day 1, 100% transparent  
✅ **Auto-updates bio** with current record and P/L

---

## Quick Setup (10 Minutes)

### Step 1: Create Bluesky Account
1. Go to **bsky.app**
2. Sign up with handle like `sharpmoney`
3. Leave bio blank (bot will write it)

### Step 2: Generate App Password
1. Log in → Settings (gear icon)
2. Privacy & Security → App Passwords
3. Click "Add App Password"
4. Name it "sharp-money-bot"
5. **Copy the password immediately** (shown once)

### Step 3: Get Odds API Key
1. Go to **the-odds-api.com**
2. Sign up (free)
3. Copy API key from dashboard

### Step 4: Create GitHub Repo
1. Go to **github.com** → New repository
2. Name: `sharp-money-bot`
3. Keep it **Public** (required for free Actions)
4. Click Create

### Step 5: Upload Files
1. On repo page → Add file → Upload files
2. Drag ALL files from this ZIP
3. Commit

**IMPORTANT:** For the workflow file:
- First create path: `.github/workflows/`
- Then upload `daily_picks.yml` into it

### Step 6: Add Secrets
1. Repo → Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Add these 3 secrets:

| Name | Value |
|------|-------|
| `BLUESKY_HANDLE` | your-handle.bsky.social |
| `BLUESKY_PASSWORD` | App password from Step 2 |
| `ODDS_API_KEY` | API key from Step 3 |

### Step 7: Enable Workflow Permissions
1. Settings → Actions → General
2. Scroll to "Workflow permissions"
3. Select **"Read and write permissions"**
4. Check **"Allow GitHub Actions to create and approve pull requests"**
5. Save

### Step 8: First Run
1. Actions tab → "Sharp Money Bot (Bluesky)"
2. Run workflow
3. Watch the log

**Expected first run:** "No qualifying picks found" (normal until game day)

---

## How It Works Daily

**5:00 PM ET** — Bot runs automatically:
1. Grade yesterday's picks (ESPN scores)
2. Fetch today's odds + splits
3. Apply 20% differential threshold
4. Post qualifying picks (if any)
5. Update bio with latest record
6. Commit updated ledger to GitHub

**On 1st of month:** Posts summary of previous month's performance

---

## Testing Without Live Data

If scrapers return empty (off-season, site issues):

1. Edit `data_fetcher.py` in GitHub
2. Scroll to bottom of `fetch_splits()` function
3. Uncomment the `return {` block with sample picks
4. Commit → Run workflow again

This tests the full pipeline with mock data.

---

## Files Explained

| File | Purpose |
|------|---------|
| `main.py` | Daily orchestrator |
| `analyser.py` | 20% threshold filter |
| `bluesky_poster.py` | Posts to Bluesky |
| `bluesky_formatter.py` | Formats posts & bio |
| `data_fetcher.py` | Scrapes free splits data |
| `record_tracker.py` | Persistent ledger |
| `result_resolver.py` | Auto-grades picks |
| `record.json` | Auto-generated ledger |
| `.github/workflows/daily_picks.yml` | Schedule |

---

## Troubleshooting

### "No workflow found in Actions tab"
- `.github/workflows/` path is wrong
- Fix: Create file at exactly `.github/workflows/daily_picks.yml`

### "401 Unauthorized"
- Handle format wrong (must include `.bsky.social`)
- App password incorrect
- Fix: Regenerate app password, update secret

### "Exit code 128" (Git error)
- Workflow permissions not enabled
- Fix: Settings → Actions → Enable "Read and write"

### "No qualifying picks" every day
- Scrapers not finding data (normal ~20-30% of time)
- Use manual override in `data_fetcher.py` to test
- Consider upgrading to paid data source for 99% uptime

---

## Monthly Summary Feature

On the 1st of each month, bot automatically posts:
```
📊 January Recap

Monthly: 12-6 (66.7%) | $+1,245
Overall: 45-22 (67.2%) | $+4,589

20%+ differential threshold
Entertainment only
```

---

## Upgrading to Paid Data (Optional)

For 99% uptime, subscribe to:
- **Action Network PRO** ($30/mo)
- **Sports Insights** ($50/mo)

Then edit `data_fetcher.py` to add their API.  
I can help integrate if you subscribe.

---

## Disclaimer

For educational and entertainment purposes only. Past performance does not guarantee future results. Never wager more than you can afford to lose. If gambling becomes a problem: **1-800-GAMBLER**.

---

**Questions?** Check the logs in Actions → click failed run → expand red step for error details.
