# AI Marketing Reports: connect GTM, GA4, Search Console and Google Ads to scripts

Python scripts that let you (or an AI assistant such as Claude Code) pull data from **Google Tag Manager, GA4, Search Console and Google Ads** and turn it into daily and weekly reports.

The full walkthrough is in the companion blog post. This repo holds the code.

> **Nothing here contains credentials.** Keys, tokens, your IDs and generated data are git-ignored. Run `python scripts/scan_for_private_data.py` before every push.

## How access works

| Product | How the scripts sign in | Why |
|---|---|---|
| Search Console | **Your own Google account** (read-only OAuth token) | Many organisations do not let you add a service account here |
| GA4 reports | **Your own Google account** (read-only OAuth token) | Same restriction |
| GA4 settings (optional) | Your own account with `--ga4-admin` (you must be an Editor) | Only needed if you want scripts to change GA4 config |
| Google Tag Manager | Service account | Edit workspaces and create versions (a human publishes) |
| Google Ads | Service account | Reporting and Keyword Planner |

If your organisation also blocks service accounts for GTM or Ads, the same user-OAuth pattern works for those with the matching scopes; see the blog post.

## Setup

1. Create a Google Cloud project and enable: Tag Manager API, Google Analytics Admin API, Google Analytics Data API, Google Search Console API, Google Ads API.
2. Service account (GTM and Ads): create it, download the JSON key to `~/.secrets/sa.json` (never into this folder), and add its email as a user in GTM and Google Ads.
3. User sign-in (Search Console and GA4): create an OAuth client of type **Desktop app**, save it as `~/.secrets/oauth-client.json`, then run `python scripts/oauth_login.py` and choose your work account.
4. `pip install -r requirements.txt`
5. Copy `config.example.json` to `config.json` and fill in your IDs (`config.json` is git-ignored).
6. `python scripts/check_access.py` and fix whatever it reports.

## Run from the repo root

```bash
python scripts/check_access.py
python scripts/ga4_report_pull.py      # daily sessions, lead events, Search Console totals
python scripts/ga4_slices.py           # country x channel, bot-like traffic
python scripts/ga4_journey.py          # what organic visitors do after the click
python scripts/gsc_pull.py             # queries, pages, sitemaps, URL inspection
python scripts/ads_pull.py             # campaigns, spend, search terms, paid sessions
python scripts/weekly_cpl_report.py    # cost per lead + Excel workbook
python scripts/keyword_ideas.py        # Keyword Planner ideas
```

Write scripts are **dry-run by default** and never publish anything:

```bash
python scripts/gtm_sync.py             # prints the plan; add --apply to write to a GTM workspace
python scripts/ga4_configure.py        # prints the plan; add --apply to change GA4 settings
```

Everything lands in dated JSON files in `snapshots/` so every number in a report can be traced.

## Before you push anything public

```bash
python scripts/scan_for_private_data.py
git config core.hooksPath .githooks   # run the scan automatically on every commit
```

## Licence

MIT. See `LICENSE`.
