# Deployment Guide — Auto Post Reels Manim

## 1. Infrastructure Overview

```
GitHub Repository
  |
  +--> GitHub Actions (ubuntu-latest)
         |
         +--> Python 3.12
         +--> Manim CE (Cairo renderer)
         +--> FFmpeg (BGM audio mix)
         +--> LaTeX (texlive-latex-base)
         |
         +--> Facebook Graph API --> Facebook Reels
         +--> Telegram Bot API  --> Admin notifications
         +--> Gemini API        --> Content generation
```

No Vercel, no Supabase. Total infrastructure cost: $0 (all free tier).

## 2. Environment Variables

Set these as **GitHub Actions Secrets** (Settings > Secrets and variables > Actions):

| Secret | Value | Source |
|---|---|---|
| `GEMINI_API_KEY` | Your Google Gemini API key | https://aistudio.google.com/app/apikey |
| `FB_PAGE_ID` | Your Facebook Page ID | Facebook Page > About > Page ID |
| `FB_ACCESS_TOKEN` | Long-lived Facebook Page Access Token | Facebook Graph API Explorer |
| `TELEGRAM_BOT_TOKEN` | Your Telegram Bot token | @BotFather on Telegram |
| `TELEGRAM_CHAT_ID` | Your Telegram Chat ID for notifications | @userinfobot on Telegram |

### Token Notes
- **Facebook Token:** Use a System User token (long-lived, doesn't expire every 60 days). Generate via Facebook Business Settings > System Users.
- **Gemini API Key:** Free tier allows 60 requests per minute — well within 5 calls/day.

## 3. Deployment Steps

### Initial Setup
```bash
# 1. Clone repository
git clone https://github.com/YOUR_USERNAME/auto-post-reels-manim.git
cd auto-post-reels-manim

# 2. Push to GitHub
git remote add origin https://github.com/YOUR_USERNAME/auto-post-reels-manim.git
git push -u origin main

# 3. Add secrets via GitHub UI (see section 2 above)

# 4. Test run (manual trigger)
#    Go to Actions > Auto Post Reels Manim > Run workflow
```

### One-time Production Setup
1. Ensure all 5 GitHub secrets are set
2. Run `workflow_dispatch` to verify end-to-end flow
3. Check GitHub Actions logs for any errors
4. Verify video appears on Facebook Page
5. If successful, cron schedules will activate automatically

## 4. GitHub Actions Workflow

File: `.github/workflows/auto-post.yml`

| Schedule (UTC) | Local (WIB) | Description |
|---|---|---|
| 06:00 | 13:00 | Posting siang |
| 10:00 | 17:00 | Posting sore |
| 13:00 | 20:00 | Posting malam |
| 16:00 | 23:00 | Posting malam |
| 19:00 | 02:00 | Posting dini hari |

### Workflow Steps
1. **Checkout** repository
2. **Setup Python** 3.12
3. **Install system deps:** ffmpeg, texlive-latex-base, texlive-latex-extra, libpango1.0-dev (~2 min)
4. **pip install** requirements.txt (~1 min)
5. **Run bot:** `python main.py`
6. **Commit & push** updated history.json and mode.json back to repo

### Concurrency
Workflow has `concurrency: auto-post` with `cancel-in-progress: false` to prevent overlapping runs.

## 5. Monitoring

### GitHub Actions Dashboard
- Go to repo > Actions > Auto Post Reels Manim
- Green = success, Red = failure
- Click any run for full logs

### Telegram Notifications
Bot automatically sends:
- `[OK]` on successful posting
- `[ERROR]` on any failure with error details
- `[BLOCKED]` on token expiry or compliance blocks

### What to Monitor
- **Rendering time** — if Manim consistently takes >8 minutes, scenes need optimization
- **Error rate** — >5% per month needs investigation
- **Token expiry** — Telegram notifies if FB token needs refresh

## 6. Maintenance

### Token Refresh
Facebook long-lived tokens eventually expire:
1. Generate new token via Graph API Explorer
2. Update `FB_ACCESS_TOKEN` secret in GitHub
3. Run `workflow_dispatch` to verify

### LaTeX Dependency
If LaTeX install fails or takes too long:
1. Manim will fallback to non-LaTeX text rendering
2. Or modify `scenes.py` to use `Text` instead of `Tex`

### BGM Updates
Add new MP3 files to `audio/` directory:
- Files are selected randomly per session
- No reconfiguration needed

## 7. Rollback Plan

| Scenario | Action |
|---|---|
| Cron posting wrong content | Disable workflow -> fix code -> re-enable |
| History corrupted | `git checkout` previous history.json |
| Build fails after update | `git revert` last commit |
| Facebook token expired | Re-generate token, update GitHub secret |

## 8. Release Checklist

| Item | Status |
|---|---|
| Requirements complete | ✓ |
| Implementation complete | ✓ |
| Code review passed | ✓ |
| QA passed (conditional) | ✓ |
| Security review passed | ✓ |
| Environment variables configured | Requires manual setup |
| GitHub Actions workflow configured | ✓ |
| Monitoring/notifications configured | ✓ |
| Rollback defined | ✓ |
| Cron schedule defined | ✓ (5x/day) |

## 9. Pre-Production Validation Steps

Before enabling cron schedules:
1. [ ] Run `workflow_dispatch` on GitHub Actions
2. [ ] Verify Manim renders successfully (check log for render time)
3. [ ] Verify video posts to Facebook (or Telegram in debug mode)
4. [ ] Check Telegram receives the notification
5. [ ] Verify history.json is updated and committed
6. [ ] If rendering time >8 minutes, adjust scene complexity
7. [ ] Once validated, cron schedules activate automatically

## 10. Deployment Approval

**DEPLOYMENT: READY.** All gates passed. Deployment is a simple git push + GitHub secrets configuration.
