# AI Marketing Reports: connect GTM, GA4, Search Console and Google Ads to scripts

Python scripts that let you (or an AI assistant such as Claude Code) pull data from **Google Tag Manager, GA4, Search Console and Google Ads** and turn it into daily and weekly reports.

The full walkthrough is in the companion blog post. This repo holds the code.

> **Nothing here contains credentials.** Keys, tokens, your IDs and generated data are git-ignored. Run `python scripts/scan_for_private_data.py` before every push.

## How access works

Every script signs in as one **service account**: a robot user with its own JSON key. You create it once and add its email address as a user in each product. Enabling an API is not enough on its own; the robot must be a user of the product too.

| Product | Add the robot as | What the scripts do |
| --- | --- | --- |
| Search Console | A user on the property (Settings > Users and permissions) | Read queries, pages, sitemaps, URL inspection |
| GA4 | **Editor** on the property (Admin > Property access management) | Read reports; optionally change settings with `ga4_configure.py` |
| Google Tag Manager | **Edit** (or Approve) on the container | Read, edit a workspace, create versions (a human publishes) |
| Google Ads | A user on the account (Admin > Access and security) | Reporting and Keyword Planner |

You need to be an owner or admin of each product to add the robot. If you are not, ask someone who is to add the email address.

## Setup

1. Create a Google Cloud project and enable: Tag Manager API, Google Analytics Admin API, Google Analytics Data API, Google Search Console API, Google Ads API.
2. Create a service account (IAM & Admin > Service Accounts; no Cloud roles needed) and download a JSON key to `~/.secrets/sa.json`. Never put the key inside this folder. Delete the downloaded copy.
3. Add the service account's email as a user in each product (table above).
4. `pip install -r requirements.txt`
5. Copy `config.example.json` to `config.json` and fill in your IDs (`config.json` is git-ignored).
6. `python scripts/check_access.py` and fix whatever it reports. A `403` means the robot has not been added to that product yet.

Google Ads usually needs a developer token. In the setup this repo came from, Basic access on the Cloud project worked over REST without one. If you get `DEVELOPER_TOKEN_*` errors, apply for a token and add the `developer-token` header in `scripts/ads_client.py`. Calls through a manager account also need `login-customer-id`.

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
