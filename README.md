# AI Marketing Reports: connect GTM, GA4, Search Console and Google Ads to scripts

Python scripts that let you (or an AI assistant such as Claude Code) pull data from **Google Tag Manager, GA4, Search Console and Google Ads** and turn it into daily and weekly reports.

The full walkthrough is in the companion blog post. This repo holds the code.

> **Nothing here contains credentials.** Keys, tokens, your IDs and generated data are git-ignored. Run `python scripts/scan_for_private_data.py` before every push.

## How access works

Every product can be reached two ways. You choose per product in `config.json` under `auth`.

| Route | Identity | Choose it when |
| --- | --- | --- |
| `"service_account"` | A robot user with a JSON key | You own the property (or can ask an admin) and can add the robot's email as a user |
| `"user"` (default) | Your own Google account, signed in once, read-only | Your organisation limits who can add users, so you cannot add a robot |

| Product | Supported routes | Default in this repo |
| --- | --- | --- |
| Search Console | `user` or `service_account` | `user` |
| GA4 (reports and settings) | `user` or `service_account` | `user` |
| Google Tag Manager | service account | service account |
| Google Ads | service account | service account |

If you run your own organisation you can create the service account and add it to Search Console and GA4 as well, then set both to `"service_account"`. Everything else works unchanged. A service account is the tidier choice for unattended schedules because it has no browser sign-in to expire.

```json
"auth": { "search_console": "service_account", "ga4": "service_account" }
```

For GA4 settings changes (`ga4_configure.py`): with `"user"`, sign in with `python scripts/oauth_login.py --ga4-admin` and be an Editor on the property; with `"service_account"`, add the robot as Editor.

## Setup

1. Create a Google Cloud project and enable: Tag Manager API, Google Analytics Admin API, Google Analytics Data API, Google Search Console API, Google Ads API.
2. Service account: create it, download the JSON key to `~/.secrets/sa.json` (never into this folder), and add its email as a user in GTM and Google Ads (and in Search Console and GA4 if you use that route).
3. User sign-in (only if you use the `"user"` route for Search Console or GA4): create an OAuth client of type **Desktop app**, save it as `~/.secrets/oauth-client.json`, then run `python scripts/oauth_login.py` and choose your work account. If you use `"service_account"` for both, add the robot's email as a user in Search Console and GA4 instead and skip this step.
4. `pip install -r requirements.txt`
5. Copy `config.example.json` to `config.json`, fill in your IDs and choose the `auth` route per product (`config.json` is git-ignored).
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
